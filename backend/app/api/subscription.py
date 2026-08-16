"""A business's own view of its WhyNotGrace platform subscription.

Read-only. There is no self-checkout any more — plans are set by platform
staff (see app.api.platform.subscriptions), the same pattern already
established for FeatureFlag in app.api.feature_flags. Kept OWNER-only,
matching that precedent, since this is platform billing rather than a
day-to-day operational concern.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_FULL_ACCESS
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.subscription import Subscription
from app.schemas.subscription import SubscriptionOut
from app.services import subscription_service

router = APIRouter(prefix="/subscription", tags=["subscription"])


def to_out(subscription: Subscription | None) -> SubscriptionOut:
    if subscription is None:
        return SubscriptionOut(status="NOT_CONFIGURED")
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
    return to_out(subscription)
