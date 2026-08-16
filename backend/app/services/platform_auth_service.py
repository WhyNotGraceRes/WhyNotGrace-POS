"""Login/refresh/logout for WhyNotGrace's own staff. Mirrors
app.services.auth_service's shape (lockout, hash-and-rotate refresh tokens)
against platform_users/platform_refresh_tokens instead of users/refresh_tokens
— see app.models.platform_user for why these are separate tables rather than
shared ones.

No email verification here: a platform account only ever comes from another
platform admin creating it directly (see app.services.platform_service),
the same "created active, no self-service" precedent app/api/staff.py
already sets for business staff.
"""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_platform_access_token,
    generate_url_safe_token,
    hash_token,
    refresh_token_expiry,
    verify_password,
)
from app.models.platform_user import PlatformRefreshToken, PlatformUser
from app.services import audit_service

settings = get_settings()


def _lockout_message(attempts_remaining: int) -> str:
    return f"Incorrect password. {attempts_remaining} attempt(s) remaining before temporary lock."


def authenticate(db: Session, *, email: str, password: str, ip_address: str | None = None) -> PlatformUser:
    user = db.query(PlatformUser).filter(PlatformUser.email == email.lower()).first()

    generic_error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if user is None or not user.is_active:
        raise generic_error

    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        remaining_seconds = int((user.locked_until - now).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account temporarily locked. Try again in {remaining_seconds}s.",
        )

    if not verify_password(password, user.password_hash):
        # Same reasoning as auth_service.authenticate: these branches commit
        # directly because the api layer's `with transaction(db):` rolls
        # back on the HTTPException raised below, and "this attempt failed"
        # must survive that rollback.
        user.failed_login_attempts += 1
        attempts_remaining = settings.login_max_attempts - user.failed_login_attempts
        if attempts_remaining <= 0:
            user.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
            user.failed_login_attempts = 0
            db.flush()
            audit_service.record(db, action="platform_auth.login_locked", platform_user_id=user.id, ip_address=ip_address)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account locked for {settings.login_lockout_minutes} minutes due to repeated failed attempts.",
            )
        db.flush()
        audit_service.record(
            db, action="platform_auth.login_failed", platform_user_id=user.id, ip_address=ip_address,
            metadata={"attempts_remaining": attempts_remaining},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_lockout_message(attempts_remaining))

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    db.flush()

    audit_service.record(db, action="platform_auth.login_success", platform_user_id=user.id, ip_address=ip_address)
    return user


def issue_token_pair(db: Session, user: PlatformUser, *, user_agent: str | None = None, ip_address: str | None = None):
    access_token = create_platform_access_token(platform_user_id=user.id, role=user.role.value)

    raw_refresh = generate_url_safe_token()
    refresh = PlatformRefreshToken(
        platform_user_id=user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=refresh_token_expiry(),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(refresh)
    db.flush()

    return access_token, raw_refresh


def rotate_refresh_token(
    db: Session, raw_refresh_token: str, *, user_agent: str | None = None, ip_address: str | None = None
):
    token_hash = hash_token(raw_refresh_token)
    existing = db.query(PlatformRefreshToken).filter(PlatformRefreshToken.token_hash == token_hash).first()

    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    if existing is None:
        raise invalid

    now = datetime.now(timezone.utc)
    if existing.revoked_at is not None:
        # Reuse of a rotated token: revoke the whole chain, same defensive
        # response as auth_service.rotate_refresh_token, and for the same
        # reason it commits explicitly there.
        db.query(PlatformRefreshToken).filter(
            PlatformRefreshToken.platform_user_id == existing.platform_user_id,
            PlatformRefreshToken.revoked_at.is_(None),
        ).update({"revoked_at": now})
        db.commit()
        raise invalid

    if existing.expires_at <= now:
        raise invalid

    user = db.get(PlatformUser, existing.platform_user_id)
    if user is None or not user.is_active:
        raise invalid

    access_token = create_platform_access_token(platform_user_id=user.id, role=user.role.value)

    raw_new_refresh = generate_url_safe_token()
    new_refresh = PlatformRefreshToken(
        platform_user_id=user.id,
        token_hash=hash_token(raw_new_refresh),
        expires_at=refresh_token_expiry(),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(new_refresh)
    db.flush()

    existing.revoked_at = now
    existing.replaced_by_id = new_refresh.id
    db.flush()

    return access_token, raw_new_refresh, user


def revoke_refresh_token(db: Session, raw_refresh_token: str) -> None:
    token_hash = hash_token(raw_refresh_token)
    existing = db.query(PlatformRefreshToken).filter(PlatformRefreshToken.token_hash == token_hash).first()
    if existing is not None and existing.revoked_at is None:
        existing.revoked_at = datetime.now(timezone.utc)
        db.flush()
