"""Shared pytest fixtures.

These tests run against a REAL PostgreSQL database — never SQLite, never
an in-memory mock. Point TEST_DATABASE_URL at a disposable database
before running pytest, e.g.:

    postgresql+psycopg://whynotgrace:changeme_dev_password@localhost:5432/whynotgrace_test

Each test runs inside an outer transaction that is rolled back afterward
(the classic SAVEPOINT-nested-session recipe), so tests never leak state
into each other even though application code calls db.commit() internally.
"""
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://whynotgrace:changeme_dev_password@localhost:5432/whynotgrace_test",
    ),
)
os.environ.setdefault("EMAIL_BACKEND", "console")
os.environ.setdefault("JWT_SECRET", "test-secret-" + "a" * 40)
# Pin the optional-infrastructure toggles to a known baseline rather than
# inheriting whatever the developer happens to have in their .env.
# pydantic-settings gives real environment variables precedence over .env
# values, so setting them here makes the suite deterministic on any machine.
# Without this, enabling Redis locally — which the deployment guide now
# recommends — silently changes what a test like test_cache.py's "disabled by
# default is a safe no-op" is actually exercising, and it fails for a reason
# that has nothing to do with the code under test. Tests that need these
# switched on set them explicitly via monkeypatch.
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("TRUSTED_PROXY_IPS", "")

from app.core.rate_limit import limiter  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.database.session import get_db, get_qr_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import *  # noqa: E402,F401,F403  (ensures every table is registered)

TEST_DATABASE_URL = os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DATABASE_URL, future=True)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def db_session(engine):
    connection = engine.connect()
    trans = connection.begin()
    # join_transaction_mode="create_savepoint" is SQLAlchemy 2.0's built-in
    # support for this exact recipe: every session.commit() issued by app
    # code (see app.database.transaction.transaction) releases the current
    # SAVEPOINT and opens a new one instead of committing the outer
    # transaction, so changes stay visible across requests within a test
    # but the whole thing rolls back cleanly at teardown.
    session = Session(bind=connection, join_transaction_mode="create_savepoint", future=True)

    yield session

    session.close()
    trans.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    def _get_db_override():
        yield db_session

    # The rate limiter's storage is a module-level singleton (see
    # app/core/rate_limit.py) shared across the whole pytest session, keyed
    # by client IP — TestClient requests all appear to come from the same
    # address, so without resetting here, an early test exhausting e.g.
    # /auth/register's 5/hour limit would cause every later test in the
    # session to fail with 429 instead of the status it actually expects.
    # Tests that specifically exercise rate limiting reset it themselves
    # mid-test as needed (see test_rate_limiting.py).
    limiter.reset()

    # get_qr_db is a separate dependency bound to its own engine/pool (see
    # app/database/session.py's dashboard-isolation split) — it must be
    # overridden the same way as get_db, or requests through app/api/qr.py
    # would bypass this test's transactional db_session entirely and hit
    # the real qr_engine, unable to see any uncommitted fixture state.
    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_qr_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def registered_business(client):
    """Registers + auto-verifies a business/owner for tests that need an
    authenticated context without exercising the email flow itself.
    """
    payload = {
        "business_name": f"Test Restaurant {uuid.uuid4().hex[:6]}",
        "business_type": "RESTAURANT",
        "owner_first_name": "Ada",
        "owner_last_name": "Owner",
        "email": f"owner-{uuid.uuid4().hex[:8]}@example.com",
        "mobile": f"9{uuid.uuid4().int % 10**9:09d}",
        "password": "SuperSecret123",
        "confirm_password": "SuperSecret123",
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {"payload": payload, "business_id": data["business_id"], "user_id": data["user_id"]}


def verify_and_login(client, db_session, payload):
    """Helper: reads the verification code directly from the DB (since the
    email backend is console-only in tests) and completes login."""
    from app.core.security import hash_token
    from app.models.user import EmailVerificationCode, User

    user = db_session.query(User).filter(User.email == payload["email"].lower()).first()
    code_row = (
        db_session.query(EmailVerificationCode)
        .filter(EmailVerificationCode.user_id == user.id)
        .order_by(EmailVerificationCode.created_at.desc())
        .first()
    )
    # The plaintext code isn't recoverable from the hash (by design) —
    # tests instead call the service function directly to get a fresh one.
    from app.services import auth_service

    code = auth_service._issue_verification_code(db_session, user)
    db_session.flush()

    resp = client.post("/api/v1/auth/verify-email", json={"email": payload["email"], "code": code})
    assert resp.status_code == 200, resp.text

    resp = client.post(
        "/api/v1/auth/login", json={"identifier": payload["email"], "password": payload["password"]}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()
