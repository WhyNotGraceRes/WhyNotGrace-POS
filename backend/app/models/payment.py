import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PaymentMethod, PaymentStatus


class Payment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payments"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    method: Mapped[PaymentMethod] = mapped_column(nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(default=PaymentStatus.PENDING, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    provider: Mapped[str | None] = mapped_column(String(30), nullable=True)  # e.g. RAZORPAY
    provider_order_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    provider_signature: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Which drawer this money went into. Nullable because payments taken
    # before shifts existed, or with no shift open, still have to be
    # recordable — a missing shift must never block taking money.
    shift_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shift_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    received_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class IdempotencyKey(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Generic idempotency store. A (business_id, scope, key) tuple maps to
    a previously computed response so retried requests (payment capture,
    webhook delivery, order creation) never double-apply.
    """
    __tablename__ = "idempotency_keys"

    business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=True, index=True
    )
    scope: Mapped[str] = mapped_column(String(60), nullable=False)  # e.g. "order_create", "payment_capture"
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    response_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
