"""Platform staff auth: login/refresh/logout, and the wall between a
platform token and a business token — see app.models.platform_user and
app.core.platform_dependencies for why these are two structurally separate
principals rather than one User table with a nullable business_id.
"""
import uuid

from app.core.security import hash_password
from app.models.enums import PlatformRole
from app.models.platform_user import PlatformUser
from tests.helpers import platform_login, register_and_login


def _create_platform_user(db_session, *, password="PlatformPass123"):
    email = f"platform-{uuid.uuid4().hex[:8]}@example.com"
    pu = PlatformUser(
        email=email, password_hash=hash_password(password),
        first_name="Platform", last_name="Admin", role=PlatformRole.SUPERADMIN, is_active=True,
    )
    db_session.add(pu)
    db_session.flush()
    return pu, password


def test_platform_login_succeeds_with_correct_credentials(client, db_session):
    _pu, password = _create_platform_user(db_session)
    db_session.commit()
    resp = client.post("/api/v1/platform/auth/login", json={"email": _pu.email, "password": password})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "access_token" in body and "refresh_token" in body
    assert body["user"]["email"] == _pu.email
    assert body["user"]["role"] == "SUPERADMIN"


def test_platform_login_rejects_wrong_password(client, db_session):
    pu, _password = _create_platform_user(db_session)
    db_session.commit()
    resp = client.post("/api/v1/platform/auth/login", json={"email": pu.email, "password": "wrong"})
    assert resp.status_code == 401


def test_platform_refresh_and_logout(client, db_session):
    pu, password = _create_platform_user(db_session)
    db_session.commit()
    tokens = client.post("/api/v1/platform/auth/login", json={"email": pu.email, "password": password}).json()

    resp = client.post("/api/v1/platform/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200, resp.text
    new_tokens = resp.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # the rotated-out token must no longer work
    resp = client.post("/api/v1/platform/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 401

    resp = client.post("/api/v1/platform/auth/logout", json={"refresh_token": new_tokens["refresh_token"]})
    assert resp.status_code == 200
    resp = client.post("/api/v1/platform/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]})
    assert resp.status_code == 401


def test_platform_me_requires_authentication(client):
    resp = client.get("/api/v1/platform/auth/me")
    assert resp.status_code == 401


def test_a_business_token_cannot_reach_any_platform_route(client, db_session):
    """The critical isolation property: a normal owner login must not work
    as a platform credential anywhere, even by accident."""
    owner = register_and_login(client, db_session, business_name="Wall Biz 1")

    resp = client.get("/api/v1/platform/auth/me", headers=owner["headers"])
    assert resp.status_code == 401

    resp = client.get("/api/v1/platform/businesses", headers=owner["headers"])
    assert resp.status_code == 401


def test_a_platform_token_cannot_reach_any_business_route(client, db_session):
    """The other half of the wall: a platform token must not resolve to a
    business User, even though both tokens can carry a NULL/None-shaped
    business claim in different circumstances."""
    platform_headers = platform_login(client, db_session)

    resp = client.get("/api/v1/auth/me", headers=platform_headers)
    assert resp.status_code == 401

    resp = client.get("/api/v1/orders", headers=platform_headers)
    assert resp.status_code == 401


def test_platform_login_is_locked_out_after_repeated_failures(client, db_session):
    """A platform account is strictly more sensitive than a business one —
    it can touch every tenant — so it gets at least the same lockout
    protection as app.models.user.User."""
    pu, password = _create_platform_user(db_session)
    db_session.commit()

    for _ in range(3):
        resp = client.post("/api/v1/platform/auth/login", json={"email": pu.email, "password": "wrong"})

    assert resp.status_code == 423

    # even the correct password is rejected while locked
    resp = client.post("/api/v1/platform/auth/login", json={"email": pu.email, "password": password})
    assert resp.status_code == 423


def test_inactive_platform_user_cannot_log_in(client, db_session):
    pu, password = _create_platform_user(db_session)
    pu.is_active = False
    db_session.commit()

    resp = client.post("/api/v1/platform/auth/login", json={"email": pu.email, "password": password})
    assert resp.status_code == 401
