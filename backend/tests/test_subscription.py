"""₹699/month platform subscription tests.

Razorpay's real order-create API call (subscription_service.create_checkout
-> razorpay_provider.create_order) cannot be exercised here — it always
makes a real HTTPS request to Razorpay, and this environment has no real
Razorpay account. This is the same honest limitation already established
for the existing restaurant-billing Razorpay flow in earlier phases: HTTP
requests here only assert behavior around that boundary (RBAC, tenant
isolation, "not configured" fails closed), while payment *verification*
(a pure local HMAC computation — see razorpay.Utility.verify_payment_signature,
which never makes a network call) is tested for real, directly against the
service layer, computing genuine signatures with a monkeypatched platform
Razorpay secret — exactly mirroring the pattern already used in
test_integration_security.py for the per-business Razorpay webhook tests.
"""
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import get_settings
from app.models.enums import PaymentStatus, SubscriptionStatus
from app.models.subscription import Subscription, SubscriptionPayment
from app.schemas.subscription import SubscriptionVerifyRequest
from app.services import subscription_service
from tests.helpers import register_and_login


@pytest.fixture()
def platform_razorpay(monkeypatch):
    """Makes the PLATFORM's global Razorpay credentials "configured" for
    exactly this test, then un-configures them again afterward so other
    tests (e.g. test_integration_security.py's "fails closed" assertions)
    aren't affected by a leaked module-level lru_cache.
    """
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_platform_key")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "platform-secret-for-tests")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "platform-webhook-secret-for-tests")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _create_staff_and_login(client, owner_headers, role: str):
    email = f"staff-{uuid.uuid4().hex[:8]}@example.com"
    mobile = f"9{uuid.uuid4().int % 10**9:09d}"
    resp = client.post(
        "/api/v1/staff",
        json={
            "first_name": "Staffer", "last_name": role.title(), "email": email, "mobile": mobile,
            "password": "StaffPass123", "role": role,
        },
        headers=owner_headers,
    )
    assert resp.status_code == 201, resp.text
    resp = client.post("/api/v1/auth/login", json={"identifier": email, "password": "StaffPass123"})
    assert resp.status_code == 200, resp.text
    return {"headers": {"Authorization": f"Bearer {resp.json()['access_token']}"}}


def test_no_subscription_is_not_configured(client, db_session):
    owner = register_and_login(client, db_session, business_name="Sub Biz 1")
    resp = client.get("/api/v1/subscription", headers=owner["headers"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "NOT_CONFIGURED"
    assert body["amount"] == 699.0
    assert body["currency"] == "INR"
    assert body["billing_interval"] == "monthly"
    assert body["subscription_id"] is None
    assert body["current_period_start"] is None


def test_subscription_endpoints_require_owner_role(client, db_session):
    owner = register_and_login(client, db_session, business_name="Sub Biz 2")

    for role in ["MANAGER", "CASH_COUNTER", "SERVICE_COUNTER", "KITCHEN"]:
        staff = _create_staff_and_login(client, owner["headers"], role)
        resp = client.get("/api/v1/subscription", headers=staff["headers"])
        assert resp.status_code == 403, f"{role} should not be able to view the subscription"

        resp = client.post("/api/v1/subscription/checkout", headers=staff["headers"])
        assert resp.status_code == 403, f"{role} should not be able to checkout"

        resp = client.post("/api/v1/subscription/cancel", headers=staff["headers"])
        assert resp.status_code == 403, f"{role} should not be able to cancel"


def test_unauthenticated_request_rejected(client):
    resp = client.get("/api/v1/subscription")
    assert resp.status_code == 401


def test_checkout_fails_closed_without_platform_credentials_and_leaves_no_orphan_row(client, db_session):
    owner = register_and_login(client, db_session, business_name="Sub Biz 3")

    resp = client.post("/api/v1/subscription/checkout", headers=owner["headers"])
    assert resp.status_code == 503, resp.text

    # The failed attempt must not leave a dangling PENDING subscription —
    # the whole attempt rolls back together (see database/transaction.py).
    resp = client.get("/api/v1/subscription", headers=owner["headers"])
    assert resp.json()["status"] == "NOT_CONFIGURED"


def test_cancel_without_subscription_returns_404(client, db_session):
    owner = register_and_login(client, db_session, business_name="Sub Biz 4")
    resp = client.post("/api/v1/subscription/cancel", headers=owner["headers"])
    assert resp.status_code == 404


def _seed_pending_payment(db_session, business_id, *, provider_order_id="order_test_123"):
    subscription = Subscription(
        business_id=business_id, plan_name=subscription_service.PLAN_NAME, amount=subscription_service.PLAN_AMOUNT,
        currency=subscription_service.PLAN_CURRENCY, billing_interval=subscription_service.PLAN_INTERVAL,
        status=SubscriptionStatus.PENDING,
    )
    db_session.add(subscription)
    db_session.flush()
    now = datetime.now(timezone.utc)
    payment = SubscriptionPayment(
        business_id=business_id, subscription_id=subscription.id, status=PaymentStatus.PENDING,
        amount=subscription_service.PLAN_AMOUNT, currency=subscription_service.PLAN_CURRENCY, provider="RAZORPAY",
        provider_order_id=provider_order_id, period_start=now, period_end=now + timedelta(days=30),
    )
    db_session.add(payment)
    db_session.flush()
    return subscription, payment


def test_verify_with_real_signature_activates_subscription(client, db_session, platform_razorpay):
    """Directly exercises the real (non-mocked) HMAC verification logic
    used by subscription_service.verify_checkout — see module docstring
    for why this goes through the service layer rather than HTTP: the
    checkout step that would normally produce this payment row requires a
    real Razorpay order-create API call this environment cannot make.
    """
    owner = register_and_login(client, db_session, business_name="Sub Biz 5")
    business_id = uuid.UUID(owner["business_id"])
    _subscription, payment = _seed_pending_payment(db_session, business_id)
    db_session.commit()

    razorpay_payment_id = "pay_test_abc"
    msg = f"{payment.provider_order_id}|{razorpay_payment_id}"
    signature = hmac.new(b"platform-secret-for-tests", msg.encode(), hashlib.sha256).hexdigest()

    payload = SubscriptionVerifyRequest(
        subscription_payment_id=payment.id, razorpay_order_id=payment.provider_order_id,
        razorpay_payment_id=razorpay_payment_id, razorpay_signature=signature,
    )
    result = subscription_service.verify_checkout(db_session, business_id, payload)
    db_session.commit()

    assert result.status == SubscriptionStatus.ACTIVE
    assert result.current_period_start is not None
    assert result.current_period_end is not None

    db_session.refresh(payment)
    assert payment.status == PaymentStatus.SUCCESS
    assert payment.provider_payment_id == razorpay_payment_id


def test_verify_rejects_invalid_signature_and_marks_payment_failed(client, db_session, platform_razorpay):
    owner = register_and_login(client, db_session, business_name="Sub Biz 6")
    business_id = uuid.UUID(owner["business_id"])
    _subscription, payment = _seed_pending_payment(db_session, business_id)
    db_session.commit()

    payload = SubscriptionVerifyRequest(
        subscription_payment_id=payment.id, razorpay_order_id=payment.provider_order_id,
        razorpay_payment_id="pay_test_xyz", razorpay_signature="totally-wrong-signature",
    )
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        subscription_service.verify_checkout(db_session, business_id, payload)
    assert exc_info.value.status_code == 400
    db_session.commit()

    db_session.refresh(payment)
    assert payment.status == PaymentStatus.FAILED


def test_verify_is_tenant_isolated(client, db_session, platform_razorpay):
    owner_a = register_and_login(client, db_session, business_name="Sub Biz 7a")
    owner_b = register_and_login(client, db_session, business_name="Sub Biz 7b")
    business_a_id = uuid.UUID(owner_a["business_id"])
    business_b_id = uuid.UUID(owner_b["business_id"])
    _subscription, payment = _seed_pending_payment(db_session, business_a_id, provider_order_id="order_tenant_test")
    db_session.commit()

    payload = SubscriptionVerifyRequest(
        subscription_payment_id=payment.id, razorpay_order_id=payment.provider_order_id,
        razorpay_payment_id="pay_x", razorpay_signature="whatever",
    )
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        subscription_service.verify_checkout(db_session, business_b_id, payload)
    assert exc_info.value.status_code == 404


def test_get_subscription_is_tenant_isolated(client, db_session):
    owner_a = register_and_login(client, db_session, business_name="Sub Biz 8a")
    owner_b = register_and_login(client, db_session, business_name="Sub Biz 8b")
    business_a_id = uuid.UUID(owner_a["business_id"])
    _seed_pending_payment(db_session, business_a_id, provider_order_id="order_iso_test")
    db_session.commit()

    resp = client.get("/api/v1/subscription", headers=owner_b["headers"])
    assert resp.json()["status"] == "NOT_CONFIGURED"


def test_active_subscription_lazily_reports_expired_after_period_end(client, db_session):
    owner = register_and_login(client, db_session, business_name="Sub Biz 9")
    business_id = uuid.UUID(owner["business_id"])

    past = datetime.now(timezone.utc) - timedelta(days=1)
    subscription = Subscription(
        business_id=business_id, plan_name=subscription_service.PLAN_NAME, amount=subscription_service.PLAN_AMOUNT,
        currency=subscription_service.PLAN_CURRENCY, billing_interval=subscription_service.PLAN_INTERVAL,
        status=SubscriptionStatus.ACTIVE, current_period_start=past - timedelta(days=30), current_period_end=past,
    )
    db_session.add(subscription)
    db_session.commit()

    resp = client.get("/api/v1/subscription", headers=owner["headers"])
    assert resp.status_code == 200
    assert resp.json()["status"] == "EXPIRED"


def test_cancel_active_subscription(client, db_session):
    owner = register_and_login(client, db_session, business_name="Sub Biz 10")
    business_id = uuid.UUID(owner["business_id"])

    now = datetime.now(timezone.utc)
    subscription = Subscription(
        business_id=business_id, plan_name=subscription_service.PLAN_NAME, amount=subscription_service.PLAN_AMOUNT,
        currency=subscription_service.PLAN_CURRENCY, billing_interval=subscription_service.PLAN_INTERVAL,
        status=SubscriptionStatus.ACTIVE, current_period_start=now, current_period_end=now + timedelta(days=30),
    )
    db_session.add(subscription)
    db_session.commit()

    resp = client.post("/api/v1/subscription/cancel", headers=owner["headers"])
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "CANCELLED"

    # Idempotent: cancelling an already-cancelled subscription is not an error.
    resp = client.post("/api/v1/subscription/cancel", headers=owner["headers"])
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"


def test_webhook_activates_subscription_payment(client, db_session, platform_razorpay):
    owner = register_and_login(client, db_session, business_name="Sub Biz 11")
    business_id = uuid.UUID(owner["business_id"])
    _subscription, payment = _seed_pending_payment(db_session, business_id, provider_order_id="order_webhook_test")
    db_session.commit()

    raw_body = json.dumps({
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"order_id": "order_webhook_test", "id": "pay_webhook_test"}}},
    }).encode()
    signature = hmac.new(b"platform-webhook-secret-for-tests", raw_body, hashlib.sha256).hexdigest()

    resp = client.post(
        "/api/v1/payments/webhooks/razorpay",
        headers={"X-Razorpay-Signature": signature}, content=raw_body,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "PROCESSED"

    db_session.refresh(payment)
    assert payment.status == PaymentStatus.SUCCESS

    resp = client.get("/api/v1/subscription", headers=owner["headers"])
    assert resp.json()["status"] == "ACTIVE"
