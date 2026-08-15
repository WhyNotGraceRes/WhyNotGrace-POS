import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import LocationStatus, LocationType


class Location(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Generalized location: a table, a hotel room, a counter, or a
    section. The same order engine targets Location regardless of type.
    """
    __tablename__ = "locations"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location_type: Mapped[LocationType] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # table number / room number / section name
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    floor: Mapped[str | None] = mapped_column(String(50), nullable=True)
    room_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # only relevant for ROOM
    status: Mapped[LocationStatus] = mapped_column(default=LocationStatus.AVAILABLE, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    qr_code: Mapped["QRCode"] = relationship(back_populates="location", uselist=False, cascade="all, delete-orphan")


class QRCode(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "qr_codes"
    __table_args__ = (UniqueConstraint("location_id", name="uq_qr_codes_location"),)

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    location: Mapped["Location"] = relationship(back_populates="qr_code")


class QRSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Ephemeral session created when a customer scans a QR code. No
    customer account is required. The session ties cart/order activity to
    a specific business + location for a bounded window of time.
    """
    __tablename__ = "qr_sessions"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
