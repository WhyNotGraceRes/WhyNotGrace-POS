"""Password hashing, JWT issuance/verification, and secure token generation.

Design rules enforced here:
- Passwords are hashed with Argon2id only (argon2-cffi PasswordHasher default).
- Refresh tokens, email verification codes, and password reset tokens are
  never stored in plaintext — only their SHA-256 hash is persisted. The
  plaintext value is handed to the client exactly once.
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

_ph = PasswordHasher()


# ---------------------------------------------------------------------------
# Password hashing (Argon2id)
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    return _ph.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _ph.check_needs_rehash(password_hash)


# ---------------------------------------------------------------------------
# Generic secure token helpers (used for refresh tokens, email verification
# codes, and password reset tokens — anything where only a hash is stored).
# ---------------------------------------------------------------------------

def generate_url_safe_token(n_bytes: int = 32) -> str:
    return secrets.token_urlsafe(n_bytes)


def generate_numeric_code(digits: int = 6) -> str:
    """Cryptographically secure numeric code, e.g. for email verification."""
    lower = 10 ** (digits - 1)
    upper = (10 ** digits) - 1
    return str(secrets.randbelow(upper - lower + 1) + lower)


def hash_token(token: str) -> str:
    """One-way hash for opaque tokens (refresh tokens, verification codes,
    reset tokens). SHA-256 is sufficient here because these tokens are
    high-entropy secrets, not low-entropy user passwords.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_compare(a: str, b: str) -> bool:
    return secrets.compare_digest(a, b)


# ---------------------------------------------------------------------------
# JWT access tokens
# ---------------------------------------------------------------------------

class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


def create_access_token(
    *,
    user_id: uuid.UUID,
    business_id: uuid.UUID | None,
    role: str | None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "biz": str(business_id) if business_id else None,
        "role": role,
        "type": TokenType.ACCESS.value,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_expire_minutes),
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc


def refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
