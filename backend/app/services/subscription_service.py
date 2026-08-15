"""The business's own ₹699/month subscription to the WhyNotGrace platform.

CRITICAL: always paid via the platform's own global Razorpay credentials
(settings.razorpay_key_id/secret), NEVER a business's connected Razorpay
credentials (app.services.payment_service._resolve_razorpay_credentials)
— that resolver is for a business charging ITS OWN customers, which has
nothing to do with the business paying the platform. Mixing these up
would be a real security/business-logic bug, not a cosmetic one.

There is exactly one plan today (see PLAN_*). No amount is ever accepted
from the client — the server decides the charge every time, same rule as
every other payment path in this codebase.
"""
import calendar
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import PaymentStatus, SubscriptionStatus
from app.models.subscription import Subscription, SubscriptionPayment
from app.services.payments.base import PaymentProviderError, PaymentProviderNotConfigured
from app.services.payments.razorpay_provider import razorpay_provider

PLAN_NAME = "WHYNOTGRACE_MONTHLY"
PLAN_AMOUNT = 699.00
PLAN_CURRENCY = "INR"
PLAN_INTERVAL = "monthly"


def _platform_credentials() -> dict[str, str | None]:
    settings = get_settings()
    return {
        "key_id": settings.razorpay_key_id,
        "key_secret": settings.razorpay_key_secret,
        "webhook_secret": settings.razorpay_webhook_secret,
    }


def _add_one_month(dt: datetime) -> datetime:
    """Calendar-month add with end-of-month clamping (Jan 31 -> Feb 28/29),
    stdlib only — no new dependency for something this small.
    """
    year = dt.year + (dt.month // 12)
    month = dt.month % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _get_subscription_row(db: Session, business_id: uuid.UUID) -> Subscription | None:
    return db.query(Subscription).filter(Subscription.business_id == business_id).first()


def _apply_lazy_expiry(subscription: Subscription) -> None:
    """A subscription is only ever transitioned to EXPIRED lazily, on read —
    there is no background job in this deployment to sweep for expiries.
    Mutates in place; caller flushes. Honest by construction: nothing ever
    reports ACTIVE past current_period_end.
    """
    if subscription.status == SubscriptionStatus.ACTIVE and subscription.current_period_end is not None:
        if subscription.current_period_end < datetime.now(timezone.utc):
            subscription.status = SubscriptionStatus.EXPIRED


def get_subscription(db: Session, business_id: uuid.UUID) -> Subscription | None:
    subscription = _get_subscription_row(db, business_id)
    if subscription is not None:
        _apply_lazy_expiry(subscription)
        db.flush()
    return subscription


def create_checkout(db: Session, business_id: uuid.UUID) -> tuple[SubscriptionPayment, str, str | None]:
    """Creates (or reuses) the business's Subscription row and a new
    SubscriptionPayment for one ₹699 charge, then a Razorpay order for it.
    Returns (subscription_payment, provider_order_id, key_id).
    """
    subscription = _get_subscription_row(db, business_id)
    now = datetime.now(timezone.utc)

    if subscription is None:
        subscription = Subscription(
            business_id=business_id, plan_name=PLAN_NAME, amount=PLAN_AMOUNT, currency=PLAN_CURRENCY,
            billing_interval=PLAN_INTERVAL, status=SubscriptionStatus.PENDING,
        )
        db.add(subscription)
        db.flush()
    else:
        _apply_lazy_expiry(subscription)

    # Renewing before the current period ends extends from the existing
    # end date (never shortens what's already been paid for); anything
    # else (first subscribe, expired, cancelled, failed) starts fresh now.
    if subscription.status == SubscriptionStatus.ACTIVE and subscription.current_period_end is not None:
        period_start = subscription.current_period_end
    else:
        period_start = now
    period_end = _add_one_month(period_start)

    payment = SubscriptionPayment(
        business_id=business_id, subscription_id=subscription.id, status=PaymentStatus.PENDING,
        amount=PLAN_AMOUNT, currency=PLAN_CURRENCY, provider="RAZORPAY",
        period_start=period_start, period_end=period_end,
    )
    db.add(payment)
    db.flush()

    credentials = _platform_credentials()
    try:
        provider_order = razorpay_provider.create_order(
            credentials=credentials, amount_paise=int(round(PLAN_AMOUNT * 100)), currency=PLAN_CURRENCY,
            receipt=f"sub-{payment.id}",
        )
    except PaymentProviderNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except PaymentProviderError as exc:
        payment.status = PaymentStatus.FAILED
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Payment provider error") from exc

    payment.provider_order_id = provider_order.provider_order_id
    db.flush()

    return payment, provider_order.provider_order_id, credentials.get("key_id")


def _activate_from_payment(db: Session, payment: SubscriptionPayment) -> None:
    """Shared by the direct /verify call and webhook activation — both are
    just "a SubscriptionPayment's signature/webhook checked out, apply it."
    """
    payment.status = PaymentStatus.SUCCESS
    payment.verified_at = datetime.now(timezone.utc)
    db.flush()

    subscription = db.get(Subscription, payment.subscription_id)
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.current_period_start = payment.period_start
    subscription.current_period_end = payment.period_end
    db.flush()


def verify_checkout(db: Session, business_id: uuid.UUID, payload) -> Subscription:
    payment = db.query(SubscriptionPayment).filter(
        SubscriptionPayment.id == payload.subscription_payment_id, SubscriptionPayment.business_id == business_id,
    ).first()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription payment not found")

    if payment.status == PaymentStatus.SUCCESS:
        return db.get(Subscription, payment.subscription_id)  # idempotent: already verified

    if payment.provider_order_id != payload.razorpay_order_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order ID mismatch")

    credentials = _platform_credentials()
    valid = razorpay_provider.verify_payment_signature(
        credentials=credentials,
        provider_order_id=payload.razorpay_order_id,
        provider_payment_id=payload.razorpay_payment_id,
        signature=payload.razorpay_signature,
    )
    if not valid:
        payment.status = PaymentStatus.FAILED
        subscription = db.get(Subscription, payment.subscription_id)
        subscription.status = SubscriptionStatus.PAYMENT_FAILED
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment signature verification failed")

    payment.provider_payment_id = payload.razorpay_payment_id
    payment.provider_signature = payload.razorpay_signature
    _activate_from_payment(db, payment)
    return db.get(Subscription, payment.subscription_id)


def cancel_subscription(db: Session, business_id: uuid.UUID) -> Subscription:
    subscription = _get_subscription_row(db, business_id)
    if subscription is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No subscription to cancel")
    if subscription.status != SubscriptionStatus.CANCELLED:
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = datetime.now(timezone.utc)
        db.flush()
    return subscription


def try_activate_by_provider_order_id(
    db: Session, provider_order_id: str, business_id: uuid.UUID | None, provider_payment_id: str | None
) -> SubscriptionPayment | None:
    """Webhook path: mirrors payment_service's restaurant-Payment lookup,
    for the case where the incoming order_id belongs to a subscription
    charge rather than a restaurant bill. Returns the activated row, or
    None if no matching (and still-pending) subscription payment exists.
    """
    query = db.query(SubscriptionPayment).filter(SubscriptionPayment.provider_order_id == provider_order_id)
    if business_id is not None:
        query = query.filter(SubscriptionPayment.business_id == business_id)
    payment = query.first()
    if payment is None or payment.status == PaymentStatus.SUCCESS:
        return None
    payment.provider_payment_id = provider_payment_id
    _activate_from_payment(db, payment)
    return payment
