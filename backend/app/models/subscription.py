"""The business's own subscription to the WhyNotGrace platform (₹699/month)
— the platform being paid, as opposed to app.models.integration.Integration
(provider=RAZORPAY), which is a business's own account for charging ITS
customers. Always paid via the platform's global Razorpay credentials,
never a business's connected ones — see app/services/subscription_service.py.
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
    """One row per ₹699 charge attempt — mirrors app.models.payment.Payment's
    shape (provider_order_id/provider_payment_id/provider_signature) so the
    same Razorpay verification code path can be reused unmodified.
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

    # The period THIS payment buys, decided at checkout time (see
    # subscription_service.create_checkout) so verification/webhook
    # activation only ever has to copy these onto the Subscription row,
    # never recompute them.
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
