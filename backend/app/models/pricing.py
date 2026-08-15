import uuid

from sqlalchemy import Boolean, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PricingContext


class PriceRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Context-specific price override for a menu item (and optionally a
    specific variant). If no rule exists for a context, MenuItem.base_price
    (+ variant.price_delta) is used. Server is the sole authority for the
    resolved price — see app.services.pricing_service.
    """
    __tablename__ = "price_rules"
    __table_args__ = (
        UniqueConstraint("item_id", "variant_id", "context", name="uq_price_rule_item_variant_context"),
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_variants.id", ondelete="CASCADE"), nullable=True
    )
    context: Mapped[PricingContext] = mapped_column(nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
