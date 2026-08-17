import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import BillStatus


class Bill(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "bills"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("order_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="SET NULL"), nullable=True
    )
    # Internal working reference, assigned the moment the bill is opened.
    # Not the tax invoice number — it is timestamped-and-random, so it is
    # useful for staff to say aloud and useless as a legal serial.
    bill_number: Mapped[str] = mapped_column(String(40), nullable=False, index=True)

    # The actual tax invoice number, and NULL until the bill is finalised.
    # That is the whole point: if the number were assigned when the bill was
    # opened, a table that walked out would burn a number and leave a gap in
    # a series that is required to be consecutive.
    invoice_number: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    invoice_series: Mapped[str | None] = mapped_column(String(10), nullable=True)
    invoice_financial_year: Mapped[str | None] = mapped_column(String(8), nullable=True)
    invoice_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    finalised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[BillStatus] = mapped_column(default=BillStatus.OPEN, nullable=False)

    # Void, not delete. A voided invoice keeps its number and stays in the
    # series — removing it would create exactly the gap the numbering rules
    # forbid, and would also erase the evidence of the cancellation.
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    void_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    voided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # No-charge: a staff meal, or a table the owner decided not to bill. Every
    # line is comped and the bill settles at zero without a payment. It is
    # deliberately a mark on the bill rather than a BillStatus, because the
    # bill still moves through OPEN -> PAID like any other and the status
    # column answers "is money outstanding", which for an NC bill is no.
    nc_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nc_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nc_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # First print is the original; everything after it is a duplicate. Stored
    # rather than derived from the audit log so the renderer can decide what
    # to stamp on the paper without running a query per print.
    print_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_printed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    tax_total: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    service_charge_total: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    discount_total: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    # Applied after tax so the taxable value stays exact — see
    # _recompute_totals. Positive when the guest pays up, negative when down.
    round_off: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    grand_total: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    amount_paid: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    # Money handed back. Kept separate from amount_paid rather than deducted
    # from it, because the bill is a record of what was collected and a
    # refund is a second event — netting them off would erase both.
    amount_refunded: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    # Ordered explicitly: without this the lines come back in whatever order
    # Postgres returns them, so updating one row (voiding it, say) reshuffles
    # the bill under the cashier's eyes and can reorder a reprinted receipt
    # against the original. Insertion order is also the order the guest was
    # served in, which is the order they expect to read.
    items: Mapped[list["BillItem"]] = relationship(
        back_populates="bill", cascade="all, delete-orphan", order_by="BillItem.created_at"
    )

    @property
    def is_nc(self) -> bool:
        return self.nc_at is not None
    taxes: Mapped[list["BillTax"]] = relationship(back_populates="bill", cascade="all, delete-orphan")
    discounts: Mapped[list["BillDiscount"]] = relationship(back_populates="bill", cascade="all, delete-orphan")
    service_charges: Mapped[list["BillServiceCharge"]] = relationship(
        back_populates="bill", cascade="all, delete-orphan"
    )
    # viewonly: Payment rows are owned and written by payment_service, never
    # through this relationship — this exists only so a bill can show what's
    # already been collected against it (split-tender: cash + card on one
    # bill), oldest first so the list reads as a running ledger.
    payments: Mapped[list["Payment"]] = relationship(
        "Payment", primaryjoin="Bill.id == foreign(Payment.bill_id)", viewonly=True, order_by="Payment.created_at"
    )


class BillItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "bill_items"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("order_items.id", ondelete="RESTRICT"), nullable=False
    )
    item_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    line_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # A voided line is kept, not deleted. Two reasons: a bill is refreshed by
    # adding order items it does not already carry, so a deleted row would
    # simply reappear on the next refresh; and the record of what was struck
    # off, by whom and why, is exactly what an owner reviewing a shift wants
    # to see. Voided lines are excluded from every total and do not print on
    # the guest's bill.
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    void_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    voided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Complimentary is not the same act as void, even though both stop the
    # line being charged. A void says the dish was never supplied, so it
    # leaves the guest's bill entirely. A comp says it was supplied and given
    # free — the line stays on the printed bill marked NC, because the whole
    # point of comping is that the guest sees what they were given. The cost
    # also has to stay countable: food that left the kitchen unpaid is a real
    # expense, not an absence of a sale.
    comped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    comp_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    comped_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    bill: Mapped["Bill"] = relationship(back_populates="items")

    @property
    def is_voided(self) -> bool:
        return self.voided_at is not None

    @property
    def is_comped(self) -> bool:
        return self.comped_at is not None

    @property
    def is_chargeable(self) -> bool:
        """Whether this line contributes money to the bill."""
        return not self.is_voided and not self.is_comped


class BillTax(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "bill_taxes"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    bill: Mapped["Bill"] = relationship(back_populates="taxes")


class BillDiscount(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "bill_discounts"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    applied_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    bill: Mapped["Bill"] = relationship(back_populates="discounts")


class BillServiceCharge(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "bill_service_charges"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # NULL when the charge came from a FLAT band — there is no percentage to
    # show on the bill in that case, and storing a fake one would make the
    # printed invoice lie about how the number was arrived at.
    percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    # Whether this charge is part of the taxable value of supply. Almost
    # always true on a restaurant bill (service, packing and delivery
    # charges all attract GST), but a non-supply line must be excludable or
    # the bill over-taxes the guest.
    is_taxable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    bill: Mapped["Bill"] = relationship(back_populates="service_charges")
