"""Public pickup ordering flow: website -> menu -> cart -> pickup ->
customer details -> Razorpay -> verified payment -> order -> POS/KOT.
No customer account required.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter, public_checkout_key
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.enums import OrderSource
from app.schemas.order import OrderOut
from app.schemas.payment import RazorpayVerifyRequest
from app.schemas.pickup_delivery import CheckoutResponse, CheckoutVerifyRequest, PickupCheckoutRequest
from app.services import public_order_service

router = APIRouter(prefix="/pickup", tags=["pickup"])


@router.post("/{business_slug}/checkout", response_model=CheckoutResponse, status_code=201)
@limiter.limit("10/minute", key_func=public_checkout_key)
def checkout(request: Request, business_slug: str, payload: PickupCheckoutRequest, db: Session = Depends(get_db)):
    with transaction(db):
        order, payment, provider_order_id, razorpay_key_id = public_order_service.checkout(
            db, business_slug=business_slug, source=OrderSource.PICKUP,
            customer_info=payload.customer, items=payload.items, notes=payload.notes,
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
def order_status(business_slug: str, order_id, db: Session = Depends(get_db)):
    from app.services import order_service, qr_service

    business = qr_service.get_business_by_slug_or_404(db, business_slug)
    return OrderOut.model_validate(order_service.get_order_or_404(db, business.id, order_id))
