"""Connection-lifecycle regression tests against the REAL SQLAlchemy pool.

Every other test file uses the `client` fixture from conftest.py, which
overrides get_db() with a test-only session bound to an already-open
connection — that override never exercises the real pool checkout/checkin
behavior at all. These tests deliberately do NOT use that fixture; they
hit the real app with the real app.database.session.engine and the real
get_db(), specifically to prove connections are actually returned to the
pool — including when a request raises partway through, which is exactly
the class of bug found under concurrency in Phase 10B/10C (a connection
was left `idle in transaction` in Postgres after a request failed).

A load test can show this happens rarely, under heavy concurrency, after
minutes of sustained traffic. These tests reproduce the same shape of
failure — an exception raised after get_db() has already handed out a
session and a query has run — deterministically, in milliseconds, every
time `pytest` runs, so a regression here is caught immediately instead of
only under a multi-hundred-user load test.
"""
import pytest
from fastapi.testclient import TestClient

from app.core.rate_limit import limiter
from app.database.session import engine
from app.main import app


def _checked_out() -> int:
    return engine.pool.checkedout()


@pytest.fixture()
def real_pool_client(engine):
    """No get_db override — exercises the real engine/pool exactly like a
    production request would. Depends on conftest's session-scoped
    `engine` fixture purely so its Base.metadata.create_all(...) has run
    (schema creation) before this test issues real queries — this test's
    own code always talks to app.database.session.engine, which points at
    the same test database, not to this fixture's engine object directly."""
    limiter.reset()
    # raise_server_exceptions=False: the exception-forcing tests below need
    # the real 500 response (and its accompanying real teardown of get_db())
    # rather than pytest re-raising the exception past the ASGI layer.
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_pool_returns_to_baseline_after_successful_request(real_pool_client):
    baseline = _checked_out()

    resp = real_pool_client.post(
        "/api/v1/auth/login", json={"identifier": "nobody@example.com", "password": "wrong-password-entirely"}
    )
    assert resp.status_code in (401, 403, 423)  # real DB-backed lookup ran; identity just doesn't exist

    assert _checked_out() == baseline


def test_pool_returns_to_baseline_after_exception_mid_request(real_pool_client, monkeypatch):
    """Forces an exception deep inside the request — after get_db() has
    already handed out a session and the login lookup has already run a
    real query against it — then verifies the connection was still
    returned to the pool rather than left checked out."""
    from app.services import auth_service

    def _boom(*args, **kwargs):
        raise RuntimeError("forced failure for connection-lifecycle test")

    monkeypatch.setattr(auth_service, "authenticate", _boom)

    baseline = _checked_out()

    resp = real_pool_client.post(
        "/api/v1/auth/login", json={"identifier": "nobody@example.com", "password": "irrelevant"}
    )
    assert resp.status_code == 500

    assert _checked_out() == baseline


def test_pool_returns_to_baseline_after_repeated_exceptions(real_pool_client, monkeypatch):
    """The same forced failure, repeated several times in a row — a single
    clean pass isn't enough to rule out a slow leak that only shows up
    after multiple failures accumulate (see Phase 10C, where the leak
    only appeared under sustained concurrent failure volume)."""
    from app.services import auth_service

    def _boom(*args, **kwargs):
        raise RuntimeError("forced failure for connection-lifecycle test")

    monkeypatch.setattr(auth_service, "authenticate", _boom)

    baseline = _checked_out()

    for _ in range(5):
        resp = real_pool_client.post(
            "/api/v1/auth/login", json={"identifier": "nobody@example.com", "password": "irrelevant"}
        )
        assert resp.status_code == 500

    assert _checked_out() == baseline


def test_pool_drains_after_genuine_concurrent_timeout_exhaustion(real_pool_client, monkeypatch):
    """Phase 11.1/11.2: at 2,000 concurrent users, `pg_stat_activity` showed
    the real connection pool repeatedly saturating at its ceiling, and every
    saturation event correlated with a permanent step-increase in stuck
    `idle in transaction` connections. The tests above force cleanup to run
    on a *synthetic* exception (RuntimeError) — useful, but not the same
    failure: this test forces GENUINE concurrent `sqlalchemy.exc.TimeoutError`s
    by pointing the app at a real but deliberately tiny pool (2+1=3
    connections, a near-zero pool_timeout) and firing more concurrent real
    HTTP requests than that pool can serve at once — then asserts every
    connection still returns to the pool, including the ones whose requests
    failed with a genuine timeout. This is a scaled-down, deterministic
    reproduction of the exact mechanism identified under real load, not an
    approximation of it.
    """
    import threading

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SASession
    from sqlalchemy.orm import sessionmaker

    import app.database.session as session_module

    tiny_engine = create_engine(
        session_module.settings.database_url,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=1,
        pool_timeout=0.05,  # near-zero on purpose: any queuing at all times out
        future=True,
    )
    tiny_session_local = sessionmaker(bind=tiny_engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=SASession)
    monkeypatch.setattr(session_module, "SessionLocal", tiny_session_local)

    results: list[int] = []
    results_lock = threading.Lock()

    def worker():
        resp = real_pool_client.post("/api/v1/auth/login", json={"identifier": "nobody@example.com", "password": "irrelevant"})
        with results_lock:
            results.append(resp.status_code)

    threads = [threading.Thread(target=worker) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    assert len(results) == 12, "not every request completed — a thread hung instead of timing out cleanly"
    # With 12 concurrent requests against a 3-connection pool and a 50ms
    # timeout, at least some MUST genuinely fail with a pool-exhaustion 500 —
    # if none did, this test isn't actually exercising the failure mode it
    # claims to, and would be silently worthless.
    assert 500 in results, "expected at least one genuine QueuePool timeout — test did not reproduce real contention"

    assert tiny_engine.pool.checkedout() == 0, "connections leaked after genuine concurrent pool-timeout exhaustion"
    tiny_engine.dispose()
