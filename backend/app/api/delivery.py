"""Public delivery ordering flow: website -> menu -> cart -> delivery
address -> customer details -> Razorpay -> verified payment -> order ->
POS/KOT. Staff-facing delivery status updates live here too.
"""
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_feature, require_roles
from app.core.permissions import ROLE_DELIVERY
from app.core.rate_limit import limiter
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.enums import FeatureModule, OrderSource
from app.schemas.order import OrderOut
from app.schemas.payment import RazorpayVerifyRequest
from app.schemas.pickup_delivery import (
    CheckoutResponse,
    CheckoutVerifyRequest,
    DeliveryCheckoutRequest,
    DeliveryStatusUpdateRequest,
)
from app.services import audit_service, order_service, public_order_service

router = APIRouter(prefix="/delivery", tags=["delivery"])


@router.post("/{business_slug}/checkout", response_model=CheckoutResponse, status_code=201)
@limiter.limit("10/minute")
def checkout(request: Request, business_slug: str, payload: DeliveryCheckoutRequest, db: Session = Depends(get_db)):
    with transaction(db):
        order, payment, provider_order_id, razorpay_key_id = public_order_service.checkout(
            db, business_slug=business_slug, source=OrderSource.DELIVERY,
            customer_info=payload.customer, items=payload.items, notes=payload.notes,
            delivery_address=payload.delivery_address, delivery_instructions=payload.delivery_instructions,
        )
    return CheckoutResponse(
        order=OrderOut.model_validate(order),
        payment_id=payment.id,
        razorpay_order_id=provider_order_id,
        razorpay_key_id=razorpay_key_id or "",
        amount_paise=int(round(float(payment.amount) * 100)),
    )


@router.post("/{business_slug}/verify-payment", response_model=OrderOut)
def verify_payment(business_slug: str, payload: CheckoutVerifyRequest, db: Session = Depends(get_db)):
    with transaction(db):
        order = public_order_service.verify_checkout(
            db, business_slug=business_slug,
            payload=RazorpayVerifyRequest(**payload.model_dump()),
        )
    return OrderOut.model_validate(order)


@router.get("/{business_slug}/orders/{order_id}", response_model=OrderOut)
def order_status(business_slug: str, order_id: uuid.UUID, db: Session = Depends(get_db)):
    from app.services import qr_service

    business = qr_service.get_business_by_slug_or_404(db, business_slug)
    return OrderOut.model_validate(order_service.get_order_or_404(db, business.id, order_id))


@router.get("/orders", response_model=list[OrderOut])
def list_delivery_orders(
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_DELIVERY)),
    _feature=Depends(require_feature(FeatureModule.DELIVERY)),
):
    return [
        OrderOut.model_validate(o)
        for o in order_service.list_orders(db, business_id, source=OrderSource.DELIVERY)
    ]


@router.put("/orders/{order_id}/status", response_model=OrderOut)
def update_delivery_status(
    order_id: uuid.UUID,
    payload: DeliveryStatusUpdateRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_DELIVERY)),
    _feature=Depends(require_feature(FeatureModule.DELIVERY)),
):
    with transaction(db):
        order = order_service.update_delivery_status(db, business_id, order_id, payload.status.value)
        audit_service.record(
            db, action="delivery.status_update", business_id=business_id, user_id=user.id,
            resource_type="order", resource_id=str(order_id), metadata={"status": payload.status.value},
        )
    return OrderOut.model_validate(order)
