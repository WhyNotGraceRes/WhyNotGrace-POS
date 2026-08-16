import uuid

from tests.helpers import register_and_login


def test_wrong_password_lockout_after_three_attempts(client, db_session):
    ctx = register_and_login(client, db_session)
    payload = ctx["payload"]

    for expected_remaining in (2, 1):
        resp = client.post(
            "/api/v1/auth/login", json={"identifier": payload["email"], "password": "wrong-password"}
        )
        assert resp.status_code == 401
        assert str(expected_remaining) in resp.json()["detail"]

    # third failed attempt locks the account
    resp = client.post("/api/v1/auth/login", json={"identifier": payload["email"], "password": "wrong-password"})
    assert resp.status_code == 423

    # even the correct password is rejected while locked
    resp = client.post(
        "/api/v1/auth/login", json={"identifier": payload["email"], "password": payload["password"]}
    )
    assert resp.status_code == 423


def test_successful_login_resets_failed_attempts(client, db_session):
    from app.models.user import User

    ctx = register_and_login(client, db_session)
    payload = ctx["payload"]
    user = db_session.query(User).filter(User.email == payload["email"].lower()).first()

    client.post("/api/v1/auth/login", json={"identifier": payload["email"], "password": "wrong-password"})
    resp = client.post("/api/v1/auth/login", json={"identifier": payload["email"], "password": payload["password"]})
    assert resp.status_code == 200

    db_session.refresh(user)
    assert user.failed_login_attempts == 0
    assert user.locked_until is None


def test_refresh_token_rotation(client, db_session):
    ctx = register_and_login(client, db_session)
    refresh_token = ctx["tokens"]["refresh_token"]

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert new_tokens["refresh_token"] != refresh_token

    # reusing the old (rotated-out) refresh token must now fail
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401


def test_logout_revokes_refresh_token(client, db_session):
    ctx = register_and_login(client, db_session)
    refresh_token = ctx["tokens"]["refresh_token"]

    resp = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert resp.status_code == 200

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401


def test_me_requires_authentication(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_malformed_access_token_rejected(client):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-jwt-at-all"})
    assert resp.status_code == 401


def test_tampered_access_token_rejected(client, db_session):
    """A syntactically valid JWT with a bad signature (e.g. re-signed with
    a different secret, or a single flipped character) must be rejected —
    decode_token verifies the signature, not just the JWT shape."""
    ctx = register_and_login(client, db_session)
    real_token = ctx["tokens"]["access_token"]
    tampered = real_token[:-4] + ("0000" if real_token[-4:] != "0000" else "1111")
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered}"})
    assert resp.status_code == 401


def test_expired_access_token_rejected(client, db_session):
    import uuid as uuid_mod
    from datetime import datetime, timedelta, timezone

    from jose import jwt

    from app.core.config import get_settings

    ctx = register_and_login(client, db_session)
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": ctx["user_id"], "biz": ctx["business_id"], "role": "OWNER", "type": "access",
        "iat": now - timedelta(minutes=30), "exp": now - timedelta(minutes=15), "jti": str(uuid_mod.uuid4()),
    }
    expired_token = jwt.encode(expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401


def test_refresh_token_cannot_be_used_as_access_token(client, db_session):
    """The refresh token is a random opaque string (secrets.token_urlsafe),
    not a JWT (see core/security.generate_url_safe_token) — presenting it
    as a Bearer access token must fail JWT decoding, not be silently
    accepted as if it carried a valid access-token claim set."""
    ctx = register_and_login(client, db_session)
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {ctx['tokens']['refresh_token']}"})
    assert resp.status_code == 401


def test_me_returns_current_user(client, db_session):
    ctx = register_and_login(client, db_session)
    resp = client.get("/api/v1/auth/me", headers=ctx["headers"])
    assert resp.status_code == 200
    assert resp.json()["email"] == ctx["payload"]["email"].lower()


def test_forgot_password_does_not_reveal_account_existence(client):
    resp_existing = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert resp_existing.status_code == 200
    assert "reset link has been sent" in resp_existing.json()["message"]


def test_forgot_password_is_rate_limited(client, db_session):
    """A repeated forgot-password request within the cooldown window must
    not create a second token or send a second email — but must still
    return the exact same generic response, so the rate limit itself
    can't be used to distinguish existing accounts from non-existent ones.
    """
    from app.models.user import PasswordResetToken

    ctx = register_and_login(client, db_session)

    resp1 = client.post("/api/v1/auth/forgot-password", json={"email": ctx["payload"]["email"]})
    assert resp1.status_code == 200

    resp2 = client.post("/api/v1/auth/forgot-password", json={"email": ctx["payload"]["email"]})
    assert resp2.status_code == 200
    assert resp2.json() == resp1.json()

    count = (
        db_session.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == uuid.UUID(ctx["user_id"]))
        .count()
    )
    assert count == 1


def test_security_headers_present_on_every_response(client):
    resp = client.get("/health")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_password_reset_flow(client, db_session):
    ctx = register_and_login(client, db_session)

    from app.models.user import PasswordResetToken
    from app.services import auth_service as svc

    svc.request_password_reset(db_session, ctx["payload"]["email"])
    db_session.flush()
    token_row = (
        db_session.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == uuid.UUID(ctx["user_id"]))
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )
    # Generate a fresh raw token via the service directly (hash can't be reversed).
    from app.core.security import generate_url_safe_token, hash_token

    raw_token = generate_url_safe_token()
    token_row.token_hash = hash_token(raw_token)
    db_session.flush()

    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": "BrandNewPass123", "confirm_password": "BrandNewPass123"},
    )
    assert resp.status_code == 200

    resp = client.post(
        "/api/v1/auth/login", json={"identifier": ctx["payload"]["email"], "password": "BrandNewPass123"}
    )
    assert resp.status_code == 200
