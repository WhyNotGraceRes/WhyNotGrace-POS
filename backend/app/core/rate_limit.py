"""Application-level rate limiting (slowapi/limits), keyed by client IP.

This protects specific sensitive endpoints (auth, payments, public
ordering) against scripted abuse from a single source — it does not
replace a proxy/CDN-level limiter for general traffic shaping.

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
from slowapi.util import get_remote_address

from app.core.config import get_settings

logger = logging.getLogger("rate_limit")


def _build_limiter() -> Limiter:
    settings = get_settings()
    if not settings.redis_url:
        return Limiter(key_func=get_remote_address)
    try:
        redis_limiter = Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)
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
        return Limiter(key_func=get_remote_address)


limiter = _build_limiter()
