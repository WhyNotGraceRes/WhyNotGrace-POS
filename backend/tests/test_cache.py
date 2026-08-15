"""Tests for app.core.cache — the optional public-menu read-through cache.

Two things must both be true for this module to be safe to enable in
production:
  1. When a real (or real-enough) Redis is reachable, it actually caches,
     invalidates per-business, and never crosses a tenant boundary.
  2. When Redis is NOT configured, or configured but unreachable, every
     operation is a silent no-op — the application must keep working
     exactly as if this module didn't exist.

(2) is tested against a real disabled/unreachable config. (1) is tested
against `fakeredis`, an in-memory Redis protocol emulator — this proves
the module's own logic (key construction, JSON round-tripping,
invalidation scoping) is correct, but is NOT the same as verifying
against a real network Redis server; that distinction is called out
explicitly in the Phase 11 report rather than glossed over here.
"""
import uuid

from app.core import cache


def test_disabled_by_default_is_a_safe_no_op():
    cache.reset_for_tests()
    key = cache.menu_cache_key(uuid.uuid4(), "TABLE", "en")
    cache.set_json(key, {"hello": "world"})  # must not raise
    assert cache.get_json(key) is None  # nothing was ever actually stored


def test_unreachable_redis_degrades_gracefully(monkeypatch):
    monkeypatch.setattr(cache, "get_settings", lambda: type("S", (), {"redis_url": "redis://127.0.0.1:1/0", "public_menu_cache_ttl_seconds": 60})())
    cache.reset_for_tests()

    key = cache.menu_cache_key(uuid.uuid4(), "TABLE", "en")
    cache.set_json(key, {"hello": "world"})  # must not raise even though nothing is listening on port 1
    assert cache.get_json(key) is None
    cache.invalidate_business_menu(uuid.uuid4())  # must not raise


def test_fake_redis_round_trip_and_tenant_scoped_keys(monkeypatch):
    fakeredis = __import__("fakeredis")
    fake_client = fakeredis.FakeRedis(decode_responses=True)

    cache.reset_for_tests()
    monkeypatch.setattr(cache, "_get_client", lambda: fake_client)

    business_a = uuid.uuid4()
    business_b = uuid.uuid4()
    key_a = cache.menu_cache_key(business_a, "TABLE", "en")
    key_b = cache.menu_cache_key(business_b, "TABLE", "en")

    cache.set_json(key_a, {"categories": ["A's menu"]})
    cache.set_json(key_b, {"categories": ["B's menu"]})

    assert cache.get_json(key_a) == {"categories": ["A's menu"]}
    assert cache.get_json(key_b) == {"categories": ["B's menu"]}
    # The two businesses' keys must never collide or be constructible as
    # the same string — this is the tenant-isolation guarantee for the
    # cache layer specifically.
    assert key_a != key_b
    assert str(business_a) in key_a and str(business_a) not in key_b


def test_invalidate_business_menu_only_clears_that_businesss_keys(monkeypatch):
    fakeredis = __import__("fakeredis")
    fake_client = fakeredis.FakeRedis(decode_responses=True)

    cache.reset_for_tests()
    monkeypatch.setattr(cache, "_get_client", lambda: fake_client)

    business_a = uuid.uuid4()
    business_b = uuid.uuid4()
    key_a = cache.menu_cache_key(business_a, "TABLE", "en")
    key_b = cache.menu_cache_key(business_b, "TABLE", "en")
    cache.set_json(key_a, {"v": "a"})
    cache.set_json(key_b, {"v": "b"})

    cache.invalidate_business_menu(business_a)

    assert cache.get_json(key_a) is None  # invalidated
    assert cache.get_json(key_b) == {"v": "b"}  # untouched — cross-tenant invalidation would be a real bug
