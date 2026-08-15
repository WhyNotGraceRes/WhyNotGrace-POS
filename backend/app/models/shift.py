"""Cash drawer sessions.

This is the feature an owner actually buys a POS for. Not the menu, not the
QR codes — the ability to hand a cashier a float at 11am, take a counted
amount back at 11pm, and see whether the two agree with what the system says
was sold. Everything else is convenience; this is control.

**One open shift per user, not per business.** A drawer belongs to the
person on duty. Two cashiers working two counters each need their own float
and their own count, or a shortfall in one cannot be told apart from a
surplus in the other — which is exactly the ambiguity someone stealing would
rely on. A single-counter restaurant simply never has more than one open at
a time and never notices the distinction.

Payments and refunds carry a shift_id so the Z-report is derived from what
actually happened rather than from a time window. Deriving it from
`created_at BETWEEN opened_at AND closed_at` looks equivalent and is not: a
payment recorded a second after close, or during a clock adjustment, lands in
the wrong drawer with nothing to show it moved.
"""
import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ShiftStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class ShiftSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "shift_sessions"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ShiftStatus] = mapped_column(default=ShiftStatus.OPEN, nullable=False, index=True)

    opened_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # The cash physically in the drawer at the start.
    opening_float: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    closed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # What the cashier counted. Recorded before they are shown what was
    # expected — see the blind-count toggle. A count taken after seeing the
    # expected figure is not a count, it is a transcription.
    declared_cash: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    # What the system says should be there: float + cash taken - cash returned.
    # Frozen at close rather than recomputed on every read, so a later
    # correction elsewhere cannot quietly rewrite a variance someone was
    # already asked about.
    expected_cash: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    # declared - expected. Negative is a shortfall, positive is a surplus.
    # Stored rather than derived so it survives independently of the two
    # numbers that produced it.
    variance: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
