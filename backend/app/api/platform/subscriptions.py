import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.subscription import to_out
from app.core.platform_dependencies import get_current_platform_user
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.platform_user import PlatformUser
from app.schemas.platform import ProvisionSubscriptionRequest, RenewSubscriptionRequest
from app.schemas.subscription import SubscriptionOut
from app.services import audit_service, platform_service, subscription_service

router = APIRouter(prefix="/platform/businesses/{business_id}/subscription", tags=["platform-subscriptions"])


@router.get("", response_model=SubscriptionOut)
def get_subscription(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    _platform_user: PlatformUser = Depends(get_current_platform_user),
):
    platform_service.get_business_or_404(db, business_id)
    return to_out(subscription_service.get_subscription(db, business_id))


@router.post("/provision", response_model=SubscriptionOut)
def provision(
    business_id: uuid.UUID,
    payload: ProvisionSubscriptionRequest,
    db: Session = Depends(get_db),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    with transaction(db):
        platform_service.get_business_or_404(db, business_id)
        subscription = subscription_service.provision_plan(
            db, business_id, plan_name=payload.plan_name, amount=payload.amount,
            billing_interval=payload.billing_interval, months=payload.months, platform_user_id=platform_user.id,
        )
        audit_service.record(
            db, action="platform.subscription_provisioned", business_id=business_id, platform_user_id=platform_user.id,
            resource_type="subscription", resource_id=str(subscription.id),
            metadata={"plan_name": payload.plan_name, "amount": payload.amount, "months": payload.months},
        )
    return to_out(subscription)


@router.post("/renew", response_model=SubscriptionOut)
def renew(
    business_id: uuid.UUID,
    payload: RenewSubscriptionRequest,
    db: Session = Depends(get_db),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    """Also the reactivation path for a lapsed (GRACE or SUSPENDED) plan —
    see subscription_service.renew_plan for why there is no separate
    un-suspend action."""
    with transaction(db):
        platform_service.get_business_or_404(db, business_id)
        subscription = subscription_service.renew_plan(
            db, business_id, months=payload.months, platform_user_id=platform_user.id
        )
        audit_service.record(
            db, action="platform.subscription_renewed", business_id=business_id, platform_user_id=platform_user.id,
            resource_type="subscription", resource_id=str(subscription.id), metadata={"months": payload.months},
        )
    return to_out(subscription)


@router.post("/suspend", response_model=SubscriptionOut)
def suspend(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    with transaction(db):
        platform_service.get_business_or_404(db, business_id)
        subscription = subscription_service.suspend_plan(db, business_id, platform_user_id=platform_user.id)
        audit_service.record(
            db, action="platform.subscription_suspended", business_id=business_id, platform_user_id=platform_user.id,
            resource_type="subscription", resource_id=str(subscription.id),
        )
    return to_out(subscription)


@router.post("/cancel", response_model=SubscriptionOut)
def cancel(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    with transaction(db):
        platform_service.get_business_or_404(db, business_id)
        subscription = subscription_service.cancel_plan(db, business_id, platform_user_id=platform_user.id)
        audit_service.record(
            db, action="platform.subscription_cancelled", business_id=business_id, platform_user_id=platform_user.id,
            resource_type="subscription", resource_id=str(subscription.id),
        )
    return to_out(subscription)
