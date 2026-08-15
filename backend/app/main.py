import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.database.session import SessionLocal, engine

settings = get_settings()

logging.basicConfig(level=logging.INFO if not settings.debug else logging.DEBUG)
logger = logging.getLogger("whynotgrace")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Refuse to boot with insecure defaults in production (see requirement 54).
    settings.validate_production_safety()
    logger.info("Starting %s in %s mode", settings.app_name, settings.app_env)
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
