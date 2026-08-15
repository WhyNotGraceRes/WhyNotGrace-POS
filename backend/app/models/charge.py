"""Owner-defined charges that vary with the value of the order.

A restaurant rarely wants one flat packing or delivery fee. It wants
"₹20 packing under ₹200, ₹10 up to ₹500, free above that" — a ladder of
bands keyed on the order value. This table is that ladder, editable by the
owner rather than hardcoded.

Band boundaries are [min_amount, max_amount): the lower bound is included,
the upper bound is not. That is deliberate and it is the one place this
design refuses to follow how people speak. An owner naturally writes
"0-100, 101-500", but real bills contain paise, so an order of ₹100.50
would fall in the gap between those two rows and silently get no charge at
all. Half-open bands make gaps impossible to express by accident; the admin
UI renders them as "₹0 to under ₹100" so the boundary is never ambiguous.

Bands sharing a name form one ladder — "Packing charge" might be three
rows. Exactly one row of a ladder can apply to a given order, which
charge_service enforces by rejecting overlapping bands at write time rather
than picking a winner at bill time.
"""
import uuid

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ChargeBasis, PricingContext


class ChargeBand(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "charge_bands"
    __table_args__ = (
        UniqueConstraint("business_id", "name", "applies_to_context", "min_amount",
                         name="uq_charge_band_ladder_start"),
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Rows sharing a name are one ladder, and appear on the bill under this
    # label. Whatever is typed here is what the guest reads.
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Which fulfilment this ladder applies to. NULL means every context —
    # a service charge usually, whereas packing and delivery fees are
    # normally scoped to PICKUP/DELIVERY.
    applies_to_context: Mapped[PricingContext | None] = mapped_column(nullable=True)

    # Half-open band on the order's taxable value: min <= value < max.
    # A NULL max is the open-ended top of the ladder ("and above").
    min_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    max_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    basis: Mapped[ChargeBasis] = mapped_column(nullable=False)
    # Percent when basis is PERCENT, rupees when basis is FLAT. A value of 0
    # is meaningful and common — it is how "free above ₹500" is expressed.
    value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # Whether GST applies to this charge. Defaults true because under GST a
    # packing, delivery or service charge on a restaurant bill forms part of
    # the value of supply and is taxable. It is configurable because not
    # every line an owner adds here is a supply — a refundable deposit, for
    # instance, is not.
    is_taxable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(default=0, nullable=False)
