import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import BusinessType


class Business(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "businesses"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, unique=True, index=True)
    business_type: Mapped[BusinessType] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    settings: Mapped["BusinessSettings"] = relationship(
        back_populates="business", uselist=False, cascade="all, delete-orphan"
    )


class BusinessSettings(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Non-feature-flag business configuration: tax defaults, service
    charge defaults, default language, timezone, etc.
    """
    __tablename__ = "business_settings"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    default_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    supported_languages: Mapped[str] = mapped_column(String(100), default="en", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata", nullable=False)
    default_tax_percent: Mapped[float] = mapped_column(default=0.0, nullable=False)
    default_service_charge_percent: Mapped[float] = mapped_column(default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)

    business: Mapped["Business"] = relationship(back_populates="settings")
