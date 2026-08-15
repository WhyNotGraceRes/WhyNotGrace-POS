"""Money handed back to a guest.

A refund is recorded as its own event against a specific Payment rather than
by reducing that payment's amount. The payment is a record of money that was
genuinely collected; editing it to reflect a later reversal would destroy the
evidence of both halves and leave a bill that silently disagrees with the
cash that passed over the counter.

**Not a GST credit note.** Under GST, reversing a supply properly means
issuing a credit note with its own document number and series, which is a
separate instrument from this record and is not implemented here. This table
tracks the operational fact — cash went back, who authorised it, why — which
is what a counter needs day to day. A business that needs formal credit notes
for its returns filing still has to raise them, and the data to do so is
here.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PaymentMethod


class Refund(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "refunds"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Which payment is being reversed. Required, because "refund ₹200 against
    # this bill" is ambiguous when the guest paid partly in cash and partly by
    # card — the till needs to know which drawer the money comes out of.
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    # How the money went back, which is not always how it came in — an online
    # payment is often refunded in cash at the counter.
    method: Mapped[PaymentMethod] = mapped_column(nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    refunded_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    refunded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
