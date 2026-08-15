import uuid

from sqlalchemy import ForeignKey, Numeric, String
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
    bill_number: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[BillStatus] = mapped_column(default=BillStatus.OPEN, nullable=False)

    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    tax_total: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    service_charge_total: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    discount_total: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    grand_total: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    amount_paid: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    items: Mapped[list["BillItem"]] = relationship(back_populates="bill", cascade="all, delete-orphan")
    taxes: Mapped[list["BillTax"]] = relationship(back_populates="bill", cascade="all, delete-orphan")
    discounts: Mapped[list["BillDiscount"]] = relationship(back_populates="bill", cascade="all, delete-orphan")
    service_charges: Mapped[list["BillServiceCharge"]] = relationship(
        back_populates="bill", cascade="all, delete-orphan"
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

    bill: Mapped["Bill"] = relationship(back_populates="items")


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
    percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    bill: Mapped["Bill"] = relationship(back_populates="service_charges")
