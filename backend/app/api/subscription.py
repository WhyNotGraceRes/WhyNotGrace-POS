"""The business's own ₹699/month subscription to the WhyNotGrace platform.

OWNER-only throughout (view included) — this is platform billing, not a
day-to-day operational concern, matching the existing OWNER-only
precedent for Staff/Integrations/Feature Flags rather than the broader
OWNER+MANAGER access given to Reports/Loyalty.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_FULL_ACCESS
from app.core.rate_limit import limiter
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.subscription import Subscription
from app.schemas.subscription import SubscriptionCheckoutResponse, SubscriptionOut, SubscriptionVerifyRequest
from app.services import audit_service, subscription_service

router = APIRouter(prefix="/subscription", tags=["subscription"])


def _to_out(subscription: Subscription | None) -> SubscriptionOut:
    if subscription is None:
        return SubscriptionOut(
            status="NOT_CONFIGURED",
            plan_name=subscription_service.PLAN_NAME,
            amount=subscription_service.PLAN_AMOUNT,
            currency=subscription_service.PLAN_CURRENCY,
            billing_interval=subscription_service.PLAN_INTERVAL,
        )
    return SubscriptionOut(
        status=subscription.status.value,
        plan_name=subscription.plan_name,
        amount=float(subscription.amount),
        currency=subscription.currency,
        billing_interval=subscription.billing_interval,
        subscription_id=subscription.id,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancelled_at=subscription.cancelled_at,
    )


@router.get("", response_model=SubscriptionOut)
def get_subscription(
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    with transaction(db):
        subscription = subscription_service.get_subscription(db, business_id)
    return _to_out(subscription)


@router.post("/checkout", response_model=SubscriptionCheckoutResponse, status_code=201)
@limiter.limit("20/minute")
def checkout(
    request: Request,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    with transaction(db):
        payment, provider_order_id, key_id = subscription_service.create_checkout(db, business_id)
        audit_service.record(
            db, action="subscription.checkout_created", business_id=business_id, user_id=user.id,
            resource_type="subscription_payment", resource_id=str(payment.id),
        )
    return SubscriptionCheckoutResponse(
        subscription_payment_id=payment.id,
        razorpay_order_id=provider_order_id,
        razorpay_key_id=key_id or "",
        amount_paise=int(round(float(payment.amount) * 100)),
        currency=payment.currency,
    )


@router.post("/verify", response_model=SubscriptionOut)
@limiter.limit("20/minute")
def verify(
    request: Request,
    payload: SubscriptionVerifyRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    with transaction(db):
        subscription = subscription_service.verify_checkout(db, business_id, payload)
        audit_service.record(
            db, action="subscription.verified", business_id=business_id, user_id=user.id,
            resource_type="subscription", resource_id=str(subscription.id),
        )
    return _to_out(subscription)


@router.post("/cancel", response_model=SubscriptionOut)
def cancel(
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    with transaction(db):
        subscription = subscription_service.cancel_subscription(db, business_id)
        audit_service.record(
            db, action="subscription.cancelled", business_id=business_id, user_id=user.id,
            resource_type="subscription", resource_id=str(subscription.id),
        )
    return _to_out(subscription)
