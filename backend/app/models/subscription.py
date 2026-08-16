"""A business's subscription to the WhyNotGrace platform — the platform
being paid, as opposed to app.models.integration.Integration
(provider=RAZORPAY), which is a business's own account for charging ITS
customers. Set and renewed by platform staff (see
app.services.subscription_service and app.api.platform.subscriptions), not
self-checkout — plan_name/amount are whatever WhyNotGrace agreed with that
client, not a fixed price.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PaymentStatus, SubscriptionStatus


class Subscription(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One row per business — the business's current subscription state.
    Created on first checkout attempt, never before (a business with no
    row is simply NOT_CONFIGURED — see subscription_service.get_subscription).
    """
    __tablename__ = "subscriptions"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    plan_name: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(nullable=False)

    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SubscriptionPayment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A record of a self-checkout charge attempt from before subscriptions
    became platform-managed. Nothing creates new rows here any more (see
    app.services.subscription_service's module docstring) — kept only so
    any payment still in flight from before that change can finish
    resolving, and so the historical record isn't deleted out from under
    itself. Mirrors app.models.payment.Payment's shape
    (provider_order_id/provider_payment_id/provider_signature) so the same
    Razorpay verification code path could be reused unmodified while it
    was live.
    """
    __tablename__ = "subscription_payments"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[PaymentStatus] = mapped_column(default=PaymentStatus.PENDING, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)

    provider: Mapped[str | None] = mapped_column(String(30), nullable=True)
    provider_order_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    provider_signature: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # The period THIS payment bought, decided at checkout time so
    # verification/webhook activation only ever had to copy these onto the
    # Subscription row, never recompute them.
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
