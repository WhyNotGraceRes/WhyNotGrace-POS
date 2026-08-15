import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class RuleType:
    """String constants for LoyaltyRule.rule_type. Not a DB enum so owners
    can be given new rule types without a migration; validated in the
    service layer instead.
    """
    ORDER_COUNT_THRESHOLD = "ORDER_COUNT_THRESHOLD"   # e.g. every Nth order -> reward
    SPEND_THRESHOLD = "SPEND_THRESHOLD"               # e.g. cumulative spend >= X -> reward
    POINTS_PER_AMOUNT = "POINTS_PER_AMOUNT"           # e.g. 1 point per Rs.100 spent
    CUSTOM = "CUSTOM"


from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin  # noqa: E402


class LoyaltyRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Owner-configurable loyalty rule. Nothing is hardcoded: "every 10th
    order is free" is expressed as rule_type=ORDER_COUNT_THRESHOLD,
    threshold=10, reward_type="FREE_ITEM".
    """
    __tablename__ = "loyalty_rules"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(40), nullable=False)
    threshold: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    reward_type: Mapped[str] = mapped_column(String(40), nullable=False)  # FREE_ITEM, DISCOUNT_PERCENT, DISCOUNT_AMOUNT, POINTS
    reward_value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class LoyaltyAccount(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "loyalty_accounts"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_spend: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    points_balance: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)


class LoyaltyTransaction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "loyalty_transactions"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loyalty_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    points_delta: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)


class Reward(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A reward earned by a customer as the result of a LoyaltyRule firing."""
    __tablename__ = "rewards"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loyalty_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loyalty_rules.id", ondelete="CASCADE"), nullable=False
    )
    reward_type: Mapped[str] = mapped_column(String(40), nullable=False)
    reward_value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    is_redeemed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Redemption(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "redemptions"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reward_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rewards.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    redeemed_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
