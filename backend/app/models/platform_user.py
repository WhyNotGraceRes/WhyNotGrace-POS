"""WhyNotGrace's own staff — not scoped to any business, never to be
confused with app.models.user.User.

Deliberately a separate table (and a separate refresh-token table below)
rather than making User.business_id nullable and adding a platform role to
it. A platform account can read and change every tenant's data; a business
account can only ever touch its own. Keeping that a hard schema-level split
— two tables, two token types (see app.core.security's platform_* token
helpers) — means a bug in one auth path cannot accidentally grant the other
kind of access, which is a much better property than "the code currently
happens to check business_id is None correctly everywhere."
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PlatformRole


class PlatformUser(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "platform_users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[PlatformRole] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # A platform account is strictly more sensitive than a business one — it
    # can touch every tenant — so it gets at least the same brute-force
    # protection as app.models.user.User, not less.
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PlatformRefreshToken(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Mirrors app.models.user.RefreshToken's shape and rotation scheme
    exactly, but is a separate table on purpose — see the module docstring.
    """
    __tablename__ = "platform_refresh_tokens"

    platform_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_refresh_tokens.id", ondelete="SET NULL"), nullable=True
    )
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
