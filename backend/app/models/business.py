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
    # The total tax rate on the bill (e.g. 5.0 for a standard restaurant).
    # Stored as one number because that is how an owner and their accountant
    # think about it; the CGST/SGST presentation below is derived from it
    # rather than being two separately-editable fields that could drift.
    default_tax_percent: Mapped[float] = mapped_column(default=0.0, nullable=False)
    default_service_charge_percent: Mapped[float] = mapped_column(default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)

    # A registered business must print its GSTIN on a tax invoice. NULL means
    # unregistered or not yet configured, in which case the bill omits the
    # line rather than printing an empty label.
    gstin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # What the tax is called on the bill. "GST" here, but the product is not
    # India-only and a hardcoded label would be wrong elsewhere.
    tax_label: Mapped[str] = mapped_column(String(40), default="GST", nullable=False)
    # Intra-state supply — the normal case for a restaurant, where the guest
    # eats where the restaurant is — must show CGST and SGST as separate
    # lines at half the rate each, not one combined "GST 5%" line. Off gives
    # a single combined line, for inter-state (IGST) or non-Indian use.
    tax_split_intra_state: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    business: Mapped["Business"] = relationship(back_populates="settings")
