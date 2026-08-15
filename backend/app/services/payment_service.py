"""Payment recording and verification. CRITICAL: a Payment row is only
ever marked SUCCESS after either (a) staff physically confirm cash receipt
(CASH), or (b) Razorpay signature verification succeeds server-side, or
(c) a signature-verified Razorpay webhook confirms it. The frontend
reporting success is never sufficient by itself.
"""
import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.billing import Bill
from app.models.enums import BillStatus, IntegrationProvider, PaymentMethod, PaymentStatus, WebhookProcessStatus
from app.models.integration import WebhookEvent
from app.models.payment import IdempotencyKey, Payment
from app.services import billing_service, integration_service, subscription_service
from app.services.payments.base import PaymentProviderError, PaymentProviderNotConfigured
from app.services.payments.razorpay_provider import razorpay_provider


def _resolve_razorpay_credentials(db: Session, business_id: uuid.UUID) -> dict[str, str | None]:
    """Business-connected credentials (via /integrations/RAZORPAY/credentials)
    take priority; falls back to the global env-configured account so
    existing single-tenant deployments and tests keep working unchanged.
    Never mixes the two — a business either uses its own full credential
    set or the global one, never a hybrid of both.
    """
    business_creds = integration_service.get_business_credentials(db, business_id, IntegrationProvider.RAZORPAY)
    if business_creds.get("key_id") and business_creds.get("key_secret"):
        return {
            "key_id": business_creds.get("key_id"),
            "key_secret": business_creds.get("key_secret"),
            "webhook_secret": business_creds.get("webhook_secret"),
        }

    from app.core.config import get_settings

    settings = get_settings()
    return {
        "key_id": settings.razorpay_key_id,
        "key_secret": settings.razorpay_key_secret,
        "webhook_secret": settings.razorpay_webhook_secret,
    }


def record_cash_payment(db: Session, business_id: uuid.UUID, staff_id: uuid.UUID, payload) -> Payment:
    bill = billing_service.get_bill_or_404(db, business_id, payload.bill_id)
    if bill.status in (BillStatus.PAID, BillStatus.CANCELLED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bill is already closed")

    payment = Payment(
        business_id=business_id, bill_id=bill.id, method=payload.method, status=PaymentStatus.SUCCESS,
        amount=payload.amount, received_by_staff_id=staff_id, notes=payload.notes,
        verified_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    db.flush()

    billing_service.record_payment_applied(db, business_id, bill.id, float(payload.amount))
    return payment


def create_razorpay_order(db: Session, business_id: uuid.UUID, payload, idempotency_key: str | None = None) -> tuple[Payment, str, str | None]:
    credentials = _resolve_razorpay_credentials(db, business_id)

    if idempotency_key:
        existing_key = db.query(IdempotencyKey).filter(
            IdempotencyKey.business_id == business_id, IdempotencyKey.scope == "razorpay_order_create",
            IdempotencyKey.key == idempotency_key,
        ).first()
        if existing_key and existing_key.resource_id:
            payment = db.get(Payment, existing_key.resource_id)
            if payment:
                return payment, payment.provider_order_id, credentials.get("key_id")

    bill = billing_service.get_bill_or_404(db, business_id, payload.bill_id)
    if bill.status in (BillStatus.PAID, BillStatus.CANCELLED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bill is already closed")

    remaining = round(float(bill.grand_total) - float(bill.amount_paid), 2)
    if remaining <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bill has no remaining balance")

    payment = Payment(
        business_id=business_id, bill_id=bill.id, method=PaymentMethod.ONLINE, status=PaymentStatus.PENDING,
        amount=remaining, provider=IntegrationProvider.RAZORPAY.value,
    )
    db.add(payment)
    db.flush()

    try:
        provider_order = razorpay_provider.create_order(
            credentials=credentials, amount_paise=int(round(remaining * 100)), currency="INR", receipt=bill.bill_number
        )
    except PaymentProviderNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except PaymentProviderError as exc:
        # Commit (not just flush): the caller's `with transaction(db):`
        # rolls back on the HTTPException below, which would otherwise
        # discard this FAILED status and silently leave the payment PENDING.
        payment.status = PaymentStatus.FAILED
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Payment provider error") from exc

    payment.provider_order_id = provider_order.provider_order_id
    db.flush()

    if idempotency_key:
        db.add(
            IdempotencyKey(
                business_id=business_id, scope="razorpay_order_create", key=idempotency_key,
                resource_id=payment.id,
            )
        )
        db.flush()

    return payment, provider_order.provider_order_id, credentials.get("key_id")


def verify_razorpay_payment(db: Session, business_id: uuid.UUID, payload) -> Payment:
    payment = db.query(Payment).filter(
        Payment.id == payload.payment_id, Payment.business_id == business_id,
        Payment.provider == IntegrationProvider.RAZORPAY.value,
    ).first()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    if payment.status == PaymentStatus.SUCCESS:
        return payment  # idempotent: already verified

    if payment.provider_order_id != payload.razorpay_order_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order ID mismatch")

    credentials = _resolve_razorpay_credentials(db, business_id)
    valid = razorpay_provider.verify_payment_signature(
        credentials=credentials,
        provider_order_id=payload.razorpay_order_id,
        provider_payment_id=payload.razorpay_payment_id,
        signature=payload.razorpay_signature,
    )
    if not valid:
        # Commit before raising — see note in create_razorpay_order above.
        payment.status = PaymentStatus.FAILED
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment signature verification failed")

    payment.provider_payment_id = payload.razorpay_payment_id
    payment.provider_signature = payload.razorpay_signature
    payment.status = PaymentStatus.SUCCESS
    payment.verified_at = datetime.now(timezone.utc)
    db.flush()

    billing_service.record_payment_applied(db, business_id, payment.bill_id, float(payment.amount))
    return payment


def handle_razorpay_webhook(
    db: Session, raw_body: bytes, signature: str, business_id: uuid.UUID | None = None
) -> WebhookEvent:
    """business_id is set for the per-business webhook URL
    (/payments/webhooks/razorpay/{business_id}, configured directly in that
    business's Razorpay dashboard) and unset for the legacy single-tenant
    URL, which verifies against the global env-configured account only.
    Either way, verification always uses that business's own secret —
    never a different business's.
    """
    if business_id is not None:
        credentials = _resolve_razorpay_credentials(db, business_id)
    else:
        from app.core.config import get_settings

        settings = get_settings()
        credentials = {
            "key_id": settings.razorpay_key_id,
            "key_secret": settings.razorpay_key_secret,
            "webhook_secret": settings.razorpay_webhook_secret,
        }

    try:
        valid = razorpay_provider.verify_webhook_signature(credentials=credentials, raw_body=raw_body, signature=signature)
    except PaymentProviderNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload")

    event_id = payload.get("id") or payload.get("event", "unknown")

    existing = db.query(WebhookEvent).filter(
        WebhookEvent.provider == IntegrationProvider.RAZORPAY, WebhookEvent.provider_event_id == event_id
    ).first()
    if existing is not None:
        existing_dup = WebhookEvent(
            business_id=business_id,
            provider=IntegrationProvider.RAZORPAY, provider_event_id=f"{event_id}-dup-{uuid.uuid4().hex[:8]}",
            signature_valid=valid, raw_payload=raw_body.decode("utf-8", errors="replace"),
            status=WebhookProcessStatus.DUPLICATE,
        )
        db.add(existing_dup)
        db.flush()
        return existing_dup

    event = WebhookEvent(
        business_id=business_id,
        provider=IntegrationProvider.RAZORPAY, provider_event_id=event_id, signature_valid=valid,
        raw_payload=raw_body.decode("utf-8", errors="replace"),
        status=WebhookProcessStatus.RECEIVED,
    )
    db.add(event)
    db.flush()

    if not valid:
        # Commit before raising — see note in create_razorpay_order above.
        event.status = WebhookProcessStatus.FAILED
        event.error = "Invalid webhook signature"
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature")

    try:
        event_type = payload.get("event", "")
        entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        provider_order_id = entity.get("order_id")
        provider_payment_id = entity.get("id")

        if event_type == "payment.captured" and provider_order_id:
            payment_query = db.query(Payment).filter(
                Payment.provider == IntegrationProvider.RAZORPAY.value,
                Payment.provider_order_id == provider_order_id,
            )
            if business_id is not None:
                # This webhook URL belongs to exactly one business — never
                # let it touch another business's payment even if IDs collided.
                payment_query = payment_query.filter(Payment.business_id == business_id)
            payment = payment_query.first()
            if payment is not None and payment.status != PaymentStatus.SUCCESS:
                payment.provider_payment_id = provider_payment_id
                payment.status = PaymentStatus.SUCCESS
                payment.verified_at = datetime.now(timezone.utc)
                db.flush()
                billing_service.record_payment_applied(db, payment.business_id, payment.bill_id, float(payment.amount))
                event.business_id = payment.business_id
            elif payment is None:
                # Not a restaurant-bill payment — check whether it's a
                # platform subscription charge instead (see
                # subscription_service.py: always verified against the
                # platform's own global credentials, same ones this legacy
                # webhook URL already uses, so no extra resolution needed).
                sub_payment = subscription_service.try_activate_by_provider_order_id(
                    db, provider_order_id, business_id, provider_payment_id
                )
                if sub_payment is not None:
                    event.business_id = sub_payment.business_id

        event.status = WebhookProcessStatus.PROCESSED
        event.processed_at = datetime.now(timezone.utc)
        db.flush()
    except Exception as exc:  # noqa: BLE001
        event.status = WebhookProcessStatus.FAILED
        event.error = str(exc)
        db.commit()
        raise

    return event
