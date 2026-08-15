import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import KOTStatus


class KOT(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Kitchen Order Ticket. One KOT is generated per order (original or
    additional) so only new items are ever sent to the kitchen.
    """
    __tablename__ = "kots"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    kot_number: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[KOTStatus] = mapped_column(default=KOTStatus.NEW, nullable=False)
    special_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    items: Mapped[list["KOTItem"]] = relationship(back_populates="kot", cascade="all, delete-orphan")


class KOTItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "kot_items"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False
    )
    item_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    options_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    kot: Mapped["KOT"] = relationship(back_populates="items")
