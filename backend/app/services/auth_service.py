"""Authentication business logic for a business's own staff. Kept separate
from app/api/auth.py so it can be unit-exercised and reused. Business
provisioning lives in app.services.platform_service now, not here — see
that module for why (there is no self-registration any more).
"""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_url_safe_token,
    hash_password,
    hash_token,
    refresh_token_expiry,
    verify_password,
)
from app.models.user import PasswordResetToken, RefreshToken, User
from app.services import audit_service
from app.services.email_service import email_service

settings = get_settings()

PASSWORD_RESET_EXPIRE_MINUTES = 30
PASSWORD_RESET_COOLDOWN_SECONDS = 60


def _lockout_message(attempts_remaining: int) -> str:
    return f"Incorrect password. {attempts_remaining} attempt(s) remaining before temporary lock."


def authenticate(db: Session, *, identifier: str, password: str, ip_address: str | None = None) -> User:
    user = db.query(User).filter(
        or_(User.email == identifier.lower(), User.mobile == identifier)
    ).first()

    generic_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
    )

    if user is None or not user.is_active:
        # Do not reveal whether the account exists.
        raise generic_error

    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        remaining_seconds = int((user.locked_until - now).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account temporarily locked. Try again in {remaining_seconds}s.",
        )

    if not verify_password(password, user.password_hash):
        # NOTE: these branches call db.commit() directly, not just flush().
        # authenticate() is always invoked inside the api layer's
        # `with transaction(db):` block, which rolls back on ANY exception
        # — including the HTTPException we're about to raise here. Without
        # an explicit commit, the failed-attempt counter (and the lockout
        # itself) would be silently discarded every time, since "reject
        # this login" and "persist that it was rejected" must both survive.
        user.failed_login_attempts += 1
        attempts_remaining = settings.login_max_attempts - user.failed_login_attempts
        if attempts_remaining <= 0:
            user.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
            user.failed_login_attempts = 0
            db.flush()
            audit_service.record(
                db, action="auth.login_locked", business_id=user.business_id, user_id=user.id, ip_address=ip_address
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account locked for {settings.login_lockout_minutes} minutes due to repeated failed attempts.",
            )
        db.flush()
        audit_service.record(
            db, action="auth.login_failed", business_id=user.business_id, user_id=user.id, ip_address=ip_address,
            metadata={"attempts_remaining": attempts_remaining},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_lockout_message(attempts_remaining))

    if not user.is_email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Please verify your email before logging in")

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    db.flush()

    audit_service.record(
        db, action="auth.login_success", business_id=user.business_id, user_id=user.id, ip_address=ip_address
    )
    return user


def issue_token_pair(db: Session, user: User, *, user_agent: str | None = None, ip_address: str | None = None):
    access_token = create_access_token(user_id=user.id, business_id=user.business_id, role=user.role.value)

    raw_refresh = generate_url_safe_token()
    refresh = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=refresh_token_expiry(),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(refresh)
    db.flush()

    return access_token, raw_refresh


def rotate_refresh_token(db: Session, raw_refresh_token: str, *, user_agent: str | None = None, ip_address: str | None = None):
    token_hash = hash_token(raw_refresh_token)
    existing = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    if existing is None:
        raise invalid

    now = datetime.now(timezone.utc)
    if existing.revoked_at is not None:
        # Reuse of a revoked/rotated token indicates possible theft — revoke
        # the whole chain defensively by revoking all tokens for this user.
        # Commit explicitly: the caller's `with transaction(db):` wrapper
        # rolls back on the HTTPException we raise next, which would
        # otherwise silently undo this revocation.
        db.query(RefreshToken).filter(
            RefreshToken.user_id == existing.user_id, RefreshToken.revoked_at.is_(None)
        ).update({"revoked_at": now})
        db.commit()
        raise invalid

    if existing.expires_at <= now:
        raise invalid

    user = db.get(User, existing.user_id)
    if user is None or not user.is_active:
        raise invalid

    access_token = create_access_token(user_id=user.id, business_id=user.business_id, role=user.role.value)

    raw_new_refresh = generate_url_safe_token()
    new_refresh = RefreshToken(
        user_id=user.id,
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
    existing = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if existing is not None and existing.revoked_at is None:
        existing.revoked_at = datetime.now(timezone.utc)
        db.flush()


def request_password_reset(db: Session, email: str) -> None:
    user = db.query(User).filter(User.email == email.lower()).first()
    if user is None:
        return  # Never reveal whether the account exists.

    # Rate-limit: this must never surface a 429
    # (a different response for "exists and just requested" vs. "doesn't
    # exist" would itself leak account existence), so an over-cooldown
    # request silently no-ops — no new token, no email — while still
    # returning the same generic message as a fresh request.
    latest = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == user.id)
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )
    if latest is not None:
        elapsed = (datetime.now(timezone.utc) - latest.created_at).total_seconds()
        if elapsed < PASSWORD_RESET_COOLDOWN_SECONDS:
            return

    raw_token = generate_url_safe_token()
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_EXPIRE_MINUTES),
    )
    db.add(reset)
    db.flush()

    reset_url = f"{settings.frontend_base_url}/reset-password?token={raw_token}"
    email_service.send_email(
        to=user.email,
        subject="Reset your WhyNotGrace password",
        body=f"Reset your password using this link (valid {PASSWORD_RESET_EXPIRE_MINUTES} minutes): {reset_url}",
    )


def reset_password(db: Session, raw_token: str, new_password: str) -> None:
    token_hash = hash_token(raw_token)
    now = datetime.now(timezone.utc)
    record = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .first()
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user = db.get(User, record.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user.password_hash = hash_password(new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    record.used_at = now

    # Invalidate all active sessions on password reset.
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
    ).update({"revoked_at": now})

    db.flush()
    audit_service.record(db, action="auth.password_reset", business_id=user.business_id, user_id=user.id)
