"""Application-level rate limiting (slowapi/limits).

This protects specific sensitive endpoints (auth, payments, public
ordering) against scripted abuse from a single source — it does not
replace a proxy/CDN-level limiter for general traffic shaping.

Choosing the key is the whole game here. The default is the real client IP
(client_ip_key -> app/core/client_ip.py), which is proxy-aware: reading
request.client.host directly, as slowapi's own get_remote_address does,
returns the reverse proxy's address for every request behind a load
balancer and so turns every per-client limit into one global limit for the
entire deployment.

IP is still the wrong key for the public QR endpoints, for a reason no
proxy configuration can fix: every guest in a restaurant shares one public
IP, because they are all behind the venue's WiFi NAT (and mobile users are
behind carrier CGNAT). Keying those by IP caps a whole dining room at one
guest's allowance. They are keyed by QR session / location instead — see
qr_session_key and qr_location_key below, which is what makes a busy venue
possible without weakening the anti-abuse guarantee.

Storage backend: if REDIS_URL is configured, limits are stored in Redis and
shared correctly across every worker/instance — an exact global limit
regardless of how many processes are running. If REDIS_URL is unset (the
default, and every environment this project has actually run in so far),
storage is in-memory and per-process: with N uvicorn/gunicorn workers, each
worker enforces its own independent counters, so the *effective* limit
becomes (per-worker limit x worker count). This was true before Phase 11
too — Phase 11 only makes it fixable via configuration instead of a code
change, and documents it explicitly here since Phase 10B/10C's multi-worker
deployment made it a real (if minor, disclosed) production consideration.
The decorators on individual routes never need to change either way.

If Redis is configured but unreachable at startup, this falls back to
in-memory storage rather than crashing the app — the same "must keep
working" philosophy as app/core/cache.py, applied to rate limiting. This
fallback path is CONFIGURATION-verified only in this environment (no real
Redis server was reachable to test against — see the Phase 11 report) —
it is not the same as having verified real cross-worker shared-limit
behavior against a live Redis instance.

Never used to replace or weaken the existing per-account protections
(login lockout in auth_service.authenticate, the cooldown in
auth_service.request_password_reset / resend_verification) — those stay
exactly as they are; this is an additional, independent layer.
"""
import logging

from slowapi import Limiter
from starlette.requests import Request

from app.core.client_ip import get_client_ip
from app.core.config import get_settings

logger = logging.getLogger("rate_limit")


def client_ip_key(request: Request) -> str:
    """Default key: the real client IP, proxy-aware.

    Replaces slowapi's get_remote_address, which reads request.client.host
    directly and so collapses every user behind a reverse proxy into one
    bucket. See app/core/client_ip.py for why the forwarded header is only
    honored from configured trusted proxies.
    """
    return get_client_ip(request)


def qr_session_key(request: Request) -> str:
    """Key for public QR ordering endpoints: the guest's QR session, not
    their IP.

    A restaurant's guests are all behind one NAT — the venue's WiFi router,
    or a mobile carrier's CGNAT pool. Keying by IP means a 200-seat venue
    shares a single 20-orders/minute budget, so the limiter would reject
    legitimate guests long before the server was under any real strain.
    That is the opposite of what this limit is for: it exists to stop one
    party from scripting thousands of orders, not to cap a busy dining room.

    The QR session token is the right unit. It is per-location, unguessable
    (generate_url_safe_token), already required on every one of these
    requests, and expires — so the limit becomes "one table cannot place
    more than N orders a minute", which is both what we want to enforce and
    independent of how many guests share a public IP.

    Falls back to the client IP when there is no session token, so a caller
    that omits the header is still limited rather than unlimited.
    """
    token = request.headers.get("x-qr-session")
    if token:
        return f"qr-session:{token}"
    return get_client_ip(request)


def qr_location_key(request: Request) -> str:
    """Key for the QR scan endpoint, which runs *before* a session exists.

    Keyed by the location being scanned (one table/room), for the same
    NAT reason as qr_session_key: a whole venue must not share one budget.
    Scanning is a per-guest-arrival action, so a per-table allowance
    matches real seating turnover while still stopping someone from
    hammering one QR code to mint sessions in bulk.
    """
    location_id = request.path_params.get("location_id")
    if location_id:
        return f"qr-location:{location_id}"
    return get_client_ip(request)


def public_checkout_key(request: Request) -> str:
    """Key for the public pickup/delivery checkout endpoints.

    These stay IP-keyed — unlike QR, a pickup/delivery customer is ordering
    from their own connection rather than a venue's shared WiFi, and the
    only other candidate key (the mobile number in the request body) is
    client-supplied and freely variable, so it would be trivially bypassed.

    The IP is scoped per business so that one busy restaurant's customers
    can never consume another restaurant's budget — without this, on a
    multi-tenant platform the limit is shared across every tenant a given
    carrier-NAT pool happens to order from.
    """
    slug = request.path_params.get("business_slug", "-")
    return f"checkout:{slug}:{get_client_ip(request)}"


def _build_limiter() -> Limiter:
    settings = get_settings()
    if not settings.redis_url:
        return Limiter(key_func=client_ip_key)
    try:
        redis_limiter = Limiter(key_func=client_ip_key, storage_uri=settings.redis_url)
        # Two checks, not one: PING only proves the server is reachable —
        # `limits`' RedisStorage also needs Lua scripting (EVAL/EVALSHA) for
        # its atomic increment-and-check operations, which not every
        # Redis-protocol-compatible server implements (discovered during
        # Phase 11 testing: fakeredis's TCP server accepts PING but raises
        # "unknown command 'evalsha'", which — without this second check —
        # would only surface as a 500 on the first real rate-limited
        # request, not at startup). Failing here instead means an
        # incompatible backend degrades to in-memory limiting at boot,
        # the same safe place every other Redis failure mode falls back to.
        redis_limiter._storage.storage.ping()
        redis_limiter._storage.storage.eval("return 1", 0)
        return redis_limiter
    except Exception as exc:  # noqa: BLE001 - rate limiting must never crash the app
        logger.warning("Redis-backed rate limiting disabled: Redis at the configured URL is unreachable or missing required Lua-scripting support (%s) — falling back to in-memory (per-process) limits", exc)
        return Limiter(key_func=client_ip_key)


limiter = _build_limiter()
