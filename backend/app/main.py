import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.middleware.gzip import GZipMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.database.session import SessionLocal, engine, get_db

settings = get_settings()

logging.basicConfig(level=logging.INFO if not settings.debug else logging.DEBUG)
logger = logging.getLogger("whynotgrace")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Refuse to boot with insecure defaults in production (see requirement 54).
    settings.validate_production_safety()
    logger.info("Starting %s in %s mode", settings.app_name, settings.app_env)

    # The WebSocket connection manager needs a reference to *this* event
    # loop — the one that will actually own every WebSocket connection —
    # so that ws_manager.notify() calls made from sync request-handler
    # threads elsewhere can hand their broadcast back to it. See
    # app/core/ws_manager.py's module docstring for why that handoff is
    # necessary at all.
    from app.core.ws_manager import manager as ws_manager

    ws_manager.bind_loop(asyncio.get_running_loop())

    yield


app = FastAPI(
    title=settings.app_name,
    description="Modular restaurant + hotel operating system API",
    version="1.0.0",
    lifespan=lifespan,
    # Interactive docs (Swagger UI / ReDoc) and the raw OpenAPI schema are
    # only served outside production — they're a convenience for
    # development/staging, not something a production deployment should
    # expose publicly by default.
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class SecurityHeadersMiddleware:
    """Baseline hardening headers (MIME-sniffing/clickjacking/referrer
    protection), added on every response regardless of origin. CORS is
    handled separately above.

    Deliberately implemented as a raw ASGI middleware — wrapping just
    `send` — rather than Starlette's `BaseHTTPMiddleware` (the
    `@app.middleware("http")` decorator form used here previously).
    BaseHTTPMiddleware runs the downstream app inside its own
    `anyio.create_task_group()` to stream the response; under concurrent
    load, when a synchronous, thread-pooled dependency (get_db, used by
    every DB-backed endpoint) raises deep in the call stack — e.g. a
    SQLAlchemy QueuePool checkout timeout when the pool is exhausted — that
    exception surfaces through the task group as part of an
    ExceptionGroup instead of a plain exception. Under enough concurrent
    failures at once, this measurably prevented some get_db() generators'
    `finally: db.close()` from ever running, leaking checked-out
    connections as `idle in transaction` in Postgres (confirmed via
    SQL_POOL_PROFILING instrumentation: exact matching counts between
    unreturned pool checkouts and stuck `idle in transaction` rows during
    a 1,000-concurrent-user load test). A plain ASGI middleware has no
    task group in the request path — a downstream exception propagates as
    an ordinary Python exception, so every dependency's cleanup runs the
    same way it would with zero middleware at all.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                if settings.is_production:
                    # Only meaningful (and only safe to promise) once the
                    # deployment is actually served over HTTPS, which
                    # production is required to be.
                    headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
            await send(message)

        await self.app(scope, receive, send_with_headers)


class SubscriptionGateMiddleware:
    """Blocks a business whose subscription has lapsed past its grace
    period — see app.services.subscription_service's ACTIVE -> GRACE ->
    SUSPENDED lazy transition. Enforced here, once, rather than as a
    per-router dependency, so a new router can never simply forget to
    include it.

    Deliberately plain ASGI, not BaseHTTPMiddleware — same reasoning as
    SecurityHeadersMiddleware above. The one DB read this does per gated
    request is offloaded via run_in_threadpool rather than called directly:
    this __call__ runs on the event loop, and psycopg's sync driver would
    otherwise block it for the duration of that query, for every request
    being served by this worker, not just this one.
    """

    # Paths under the API prefix that must work even for a suspended
    # business: logging in (so staff can even see why), the platform's own
    # surface (a platform token never carries a business_id claim anyway,
    # so this is belt-and-suspenders), and reading (not writing) the two
    # things a "you're suspended" banner needs to render.
    _EXEMPT_PREFIXES = ("/auth", "/platform")
    _EXEMPT_GET_PATHS = ("/subscription", "/businesses/me")

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._prefix = get_settings().api_v1_prefix

    def _is_exempt(self, path: str, method: str) -> bool:
        if not path.startswith(self._prefix):
            # Not an authenticated staff API path at all (public QR/website/
            # pickup/delivery routes, health, docs) — nothing here applies.
            return True
        rest = path[len(self._prefix):]
        if rest.startswith(self._EXEMPT_PREFIXES):
            return True
        if method == "GET" and rest in self._EXEMPT_GET_PATHS:
            return True
        return False

    @staticmethod
    def _bearer_token(scope: Scope) -> str | None:
        for name, value in scope.get("headers", ()):
            if name == b"authorization":
                text_value = value.decode("latin-1")
                if text_value.lower().startswith("bearer "):
                    return text_value[7:].strip()
        return None

    @staticmethod
    def _is_suspended(business_id_str: str) -> bool:
        """Runs in a worker thread (see run_in_threadpool below).

        Resolves its DB session through app.dependency_overrides rather
        than opening a bare SessionLocal() directly — the two are
        equivalent in production (dependency_overrides is empty there, so
        this reduces to exactly get_db()'s own body: a fresh SessionLocal()
        per call), but they differ under test: the test suite overrides
        get_db to hand out one connection-pinned, SAVEPOINT-scoped session
        per test (see tests/conftest.py) so that app code's db.commit()
        calls stay visible within that test without ever hitting the real
        database. A bare SessionLocal() here would open an independent
        connection blind to that session's uncommitted state — a business a
        test just marked SUSPENDED would look untouched to this check,
        every time, in every test, since the two connections would never
        agree on what happened until the test's transaction actually
        committed (never — it's rolled back at teardown for isolation).
        """
        import uuid as uuid_mod

        from app.models.enums import SubscriptionStatus
        from app.services import subscription_service

        get_db_dependency = app.dependency_overrides.get(get_db, get_db)
        gen = get_db_dependency()
        db = next(gen)
        try:
            subscription = subscription_service.get_subscription(db, uuid_mod.UUID(business_id_str))
            if subscription is None:
                return False
            is_suspended = subscription.status == SubscriptionStatus.SUSPENDED
            db.commit()  # persists any lazy ACTIVE->GRACE->SUSPENDED transition just computed
            return is_suspended
        except Exception:  # noqa: BLE001
            # A malformed business_id or a transient DB error must fail
            # open here — this is a billing gate, not the authentication
            # check, and the request's real auth/business-scoping still
            # runs normally afterward regardless of what happens here.
            db.rollback()
            return False
        finally:
            # Drives get_db()'s generator to completion so its own
            # `finally: db.close()` runs — this is exactly what FastAPI's
            # dependency-injection machinery does automatically for a
            # normal route; doing it by hand here is the price of calling a
            # generator dependency directly instead of through Depends().
            try:
                next(gen)
            except StopIteration:
                pass

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or self._is_exempt(scope["path"], scope["method"]):
            await self.app(scope, receive, send)
            return

        token = self._bearer_token(scope)
        if token is None:
            await self.app(scope, receive, send)
            return

        from app.core.security import TokenType, decode_token

        try:
            payload = decode_token(token)
        except ValueError:
            # Not this middleware's job to reject a bad token — let the
            # route's own auth dependency produce the real 401.
            await self.app(scope, receive, send)
            return

        if payload.get("type") != TokenType.ACCESS.value or payload.get("actor") == "platform":
            await self.app(scope, receive, send)
            return

        business_id_str = payload.get("biz")
        if not business_id_str:
            await self.app(scope, receive, send)
            return

        if await run_in_threadpool(self._is_suspended, business_id_str):
            response = JSONResponse(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                content={"detail": "This business's subscription is suspended. Contact WhyNotGrace to reactivate it."},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


# Added first, so it sits innermost and compresses the response body before
# CORS/security headers are attached (Starlette runs the most recently added
# middleware outermost).
#
# compresslevel is deliberately 5, not gzip's default 9. The load-test
# profiling that motivated this found the app CPU-bound and the database
# nearly idle (peak backend CPU 139-206%, 2 active DB connections at 2,000
# concurrent users), so spending extra CPU to chase the last few percent of
# compression ratio would work against the exact bottleneck this is meant to
# relieve. Level 5 gets most of the size reduction for a fraction of the CPU.
#
# GZipMiddleware is a pure ASGI middleware, not a BaseHTTPMiddleware — see
# SecurityHeadersMiddleware's docstring above for why that distinction is
# load-bearing here.
app.add_middleware(
    GZipMiddleware,
    minimum_size=settings.gzip_minimum_size_bytes,
    compresslevel=5,
)
# Registered before CORSMiddleware (and so runs INSIDE it — Starlette's
# outermost-is-most-recently-added rule again) specifically so that a 402
# short-circuit from this middleware still goes out through CORS. Getting
# this backwards is a real, easy-to-hit bug, not a theoretical one: a
# cross-origin browser request that gets rejected without CORS headers
# doesn't surface as a clean 402 to the frontend at all — the browser
# blocks the response outright and JS only ever sees a generic network
# failure, with no status code and no body to read the reason from.
app.add_middleware(SubscriptionGateMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Never leak internals; return a clean, consistent error shape.
    # jsonable_encoder is required here: pydantic v2 packs the raw
    # exception object into errors()[i]["ctx"]["error"] for validators
    # that raise ValueError, which plain json.dumps cannot serialize.
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": jsonable_encoder(exc.errors())},
    )


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
def health_db():
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "detail": "database unavailable"},
        )
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
from app.api import auth, businesses, feature_flags, settings as settings_api, staff, users  # noqa: E402
from app.api import menu, categories, pricing  # noqa: E402
from app.api import locations, tables, rooms, qr  # noqa: E402
from app.api import orders, kot, kitchen  # noqa: E402
from app.api import billing, payments  # noqa: E402
from app.api import customers, loyalty, reviews  # noqa: E402
from app.api import website, pickup, delivery  # noqa: E402
from app.api import dashboard, reports  # noqa: E402
from app.api import integrations  # noqa: E402
from app.api import admin  # noqa: E402
from app.api import subscription  # noqa: E402
from app.api import channels, partner_channels  # noqa: E402
from app.api import charges  # noqa: E402
from app.api import toggles as toggles_api  # noqa: E402
from app.api import receipts  # noqa: E402
from app.api import shifts  # noqa: E402
from app.api import notifications  # noqa: E402
from app.api import ws  # noqa: E402
from app.api.platform import auth as platform_auth  # noqa: E402
from app.api.platform import businesses as platform_businesses  # noqa: E402
from app.api.platform import features as platform_features  # noqa: E402
from app.api.platform import toggles as platform_toggles  # noqa: E402
from app.api.platform import subscriptions as platform_subscriptions  # noqa: E402

prefix = settings.api_v1_prefix

app.include_router(auth.router, prefix=prefix)
app.include_router(users.router, prefix=prefix)
app.include_router(businesses.router, prefix=prefix)
app.include_router(staff.router, prefix=prefix)
app.include_router(settings_api.router, prefix=prefix)
app.include_router(feature_flags.router, prefix=prefix + "/settings", tags=["feature-flags"])
app.include_router(feature_flags.router, prefix=prefix + "/feature-flags", tags=["feature-flags"])
app.include_router(menu.router, prefix=prefix)
app.include_router(categories.router, prefix=prefix)
app.include_router(pricing.router, prefix=prefix)
app.include_router(locations.router, prefix=prefix)
app.include_router(tables.router, prefix=prefix)
app.include_router(rooms.router, prefix=prefix)
app.include_router(qr.router, prefix=prefix)
app.include_router(orders.router, prefix=prefix)
app.include_router(kot.router, prefix=prefix)
app.include_router(kitchen.router, prefix=prefix)
app.include_router(billing.router, prefix=prefix)
app.include_router(payments.router, prefix=prefix)
app.include_router(customers.router, prefix=prefix)
app.include_router(loyalty.router, prefix=prefix)
app.include_router(reviews.router, prefix=prefix)
app.include_router(website.router, prefix=prefix)
app.include_router(pickup.router, prefix=prefix)
app.include_router(delivery.router, prefix=prefix)
app.include_router(dashboard.router, prefix=prefix)
app.include_router(reports.router, prefix=prefix)
app.include_router(integrations.router, prefix=prefix)
app.include_router(admin.router, prefix=prefix)
app.include_router(subscription.router, prefix=prefix)
app.include_router(partner_channels.router, prefix=prefix)
app.include_router(channels.router, prefix=prefix)
app.include_router(charges.router, prefix=prefix)
app.include_router(toggles_api.router, prefix=prefix)
app.include_router(shifts.router, prefix=prefix)
app.include_router(receipts.router, prefix=prefix)
app.include_router(notifications.router, prefix=prefix)
app.include_router(ws.router, prefix=prefix)
app.include_router(platform_auth.router, prefix=prefix)
app.include_router(platform_businesses.router, prefix=prefix)
app.include_router(platform_features.router, prefix=prefix)
app.include_router(platform_toggles.router, prefix=prefix)
app.include_router(platform_subscriptions.router, prefix=prefix)
