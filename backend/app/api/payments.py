import uuid

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_feature, require_roles
from app.core.permissions import ROLE_BILLING
from app.core.rate_limit import limiter
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.enums import FeatureModule
from app.schemas.payment import (
    CashPaymentRequest,
    PaymentOut,
    RazorpayOrderCreateRequest,
    RazorpayOrderCreateResponse,
    RazorpayVerifyRequest,
)
from app.services import audit_service, payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/cash", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def record_cash_payment(
    payload: CashPaymentRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_BILLING)),
):
    with transaction(db):
        payment = payment_service.record_cash_payment(db, business_id, user.id, payload)
        audit_service.record(
            db, action="payment.cash_recorded", business_id=business_id, user_id=user.id,
            resource_type="payment", resource_id=str(payment.id), metadata={"amount": float(payload.amount)},
        )
    return PaymentOut.model_validate(payment)


@router.post(
    "/razorpay/order",
    response_model=RazorpayOrderCreateResponse,
    dependencies=[Depends(require_feature(FeatureModule.ONLINE_PAYMENT))],
)
@limiter.limit("20/minute")
def create_razorpay_order(
    request: Request,
    payload: RazorpayOrderCreateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_BILLING)),
):
    with transaction(db):
        payment, provider_order_id, razorpay_key_id = payment_service.create_razorpay_order(
            db, business_id, payload, idempotency_key
        )
        audit_service.record(
            db, action="payment.razorpay_order_created", business_id=business_id, user_id=user.id,
            resource_type="payment", resource_id=str(payment.id),
        )
    return RazorpayOrderCreateResponse(
        payment_id=payment.id,
        razorpay_order_id=provider_order_id,
        razorpay_key_id=razorpay_key_id or "",
        amount_paise=int(round(float(payment.amount) * 100)),
    )


@router.post("/razorpay/verify", response_model=PaymentOut)
@limiter.limit("20/minute")
def verify_razorpay_payment(
    request: Request,
    payload: RazorpayVerifyRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_BILLING)),
):
    with transaction(db):
        payment = payment_service.verify_razorpay_payment(db, business_id, payload)
        audit_service.record(
            db, action="payment.razorpay_verified", business_id=business_id, user_id=user.id,
            resource_type="payment", resource_id=str(payment.id),
        )
    return PaymentOut.model_validate(payment)


@router.post("/webhooks/razorpay", status_code=status.HTTP_200_OK)
# Deliberately not IP rate-limited: the caller is Razorpay's own
# infrastructure (not an untrusted end user), the endpoint is already
# protected by HMAC signature verification, and a legitimate burst of
# payment confirmations must never be dropped by a client-side throttle.
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(..., alias="X-Razorpay-Signature"),
    db: Session = Depends(get_db),
):
    """Legacy single-tenant webhook URL: verifies against the global
    env-configured Razorpay account only. Businesses with their own
    connected Razorpay credentials should register the per-business URL
    below in their own Razorpay dashboard instead.
    """
    raw_body = await request.body()
    with transaction(db):
        event = payment_service.handle_razorpay_webhook(db, raw_body, x_razorpay_signature)
    return {"status": event.status.value}


@router.post("/webhooks/razorpay/{business_id}", status_code=status.HTTP_200_OK)
async def razorpay_webhook_for_business(
    business_id: uuid.UUID,
    request: Request,
    x_razorpay_signature: str = Header(..., alias="X-Razorpay-Signature"),
    db: Session = Depends(get_db),
):
    """Per-business webhook URL. business_id comes only from the URL path
    (configured by that business in their own Razorpay dashboard) — it is
    never trusted from the request body, and signature verification always
    uses that exact business's connected (or global-fallback) secret.
    """
    raw_body = await request.body()
    with transaction(db):
        event = payment_service.handle_razorpay_webhook(db, raw_body, x_razorpay_signature, business_id=business_id)
    return {"status": event.status.value}
