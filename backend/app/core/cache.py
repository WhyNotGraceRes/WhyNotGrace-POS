"""Optional read-through cache for public, non-sensitive data.

Disabled by default (no REDIS_URL configured) — every function becomes a
no-op and callers transparently fall back to querying PostgreSQL, so this
module is never required for correctness, only for reducing database load
under concurrent read traffic (see qr_service.build_menu_response, the
only current caller). If Redis is configured but unreachable at startup or
at any point later (network partition, restart, eviction), every operation
catches the error, logs a warning, and degrades to the same no-op
behavior — the application must keep serving real data from Postgres
either way. This module is intentionally NOT used for anything
transactional, authorization-related, or payment-related — see the
module-level rule in app/services/qr_service.py's docstring.

Tenant safety: every key this module's callers use is namespaced with the
business_id as the FIRST segment (see `menu_cache_key`), so a cache lookup
can never be constructed without a tenant scope, and `invalidate_business_menu`
only ever deletes keys under that one business's own prefix.
"""
import json
import logging
import uuid
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger("cache")

_client = None
_client_init_attempted = False


def _get_client():
    """Lazily creates the Redis client on first use — not at import time,
    so environments/tests that never enable caching don't need `redis`
    importable at all, and so a settings change in tests takes effect
    without needing to reload this module."""
    global _client, _client_init_attempted
    if _client_init_attempted:
        return _client
    _client_init_attempted = True
    settings = get_settings()
    if not settings.redis_url:
        return None
    try:
        import redis

        client = redis.Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
            retry_on_timeout=False,
            decode_responses=True,
        )
        client.ping()
    except Exception as exc:  # noqa: BLE001 - cache must never break the app
        logger.warning("Cache disabled: could not connect to Redis (%s)", exc)
        _client = None
        return None
    _client = client
    return _client


def menu_cache_key(business_id: uuid.UUID, location_type: str, language: str) -> str:
    """Tenant-scoped cache key for a QR public menu response."""
    return f"business:{business_id}:public_menu:{location_type}:{language}"


def get_json(key: str) -> Any | None:
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cache read failed for %s (%s) — falling back to database", key, exc)
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def set_json(key: str, value: Any, ttl_seconds: int | None = None) -> None:
    client = _get_client()
    if client is None:
        return
    settings = get_settings()
    try:
        client.set(key, json.dumps(value), ex=ttl_seconds or settings.public_menu_cache_ttl_seconds)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cache write failed for %s (%s) — response was still served correctly from the database", key, exc)


def invalidate_business_menu(business_id: uuid.UUID) -> None:
    """Best-effort invalidation, called from the after-commit hook in
    app/database/session.py whenever a menu/category/item/variant/option
    write commits for this business. The TTL (public_menu_cache_ttl_seconds)
    is the actual staleness guarantee — this just shortens the typical
    window from "up to TTL" to "near-immediate" when Redis is reachable."""
    client = _get_client()
    if client is None:
        return
    try:
        pattern = f"business:{business_id}:public_menu:*"
        keys = list(client.scan_iter(match=pattern, count=100))
        if keys:
            client.delete(*keys)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Cache invalidation failed for business %s (%s) — stale entries will still expire via TTL", business_id, exc
        )


def reset_for_tests() -> None:
    """Test-only: forces re-evaluation of the Redis connection, e.g. after
    monkeypatching settings.redis_url."""
    global _client, _client_init_attempted
    _client = None
    _client_init_attempted = False
