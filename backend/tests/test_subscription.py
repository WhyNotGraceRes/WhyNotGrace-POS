"""A business's own read-only view of its WhyNotGrace platform subscription.

Provisioning/renewal/suspend/cancel are platform-only now (see
tests/test_platform_admin.py) — this file covers what's left on the
business-facing side: NOT_CONFIGURED, tenant isolation, and the lazy
ACTIVE -> GRACE -> SUSPENDED transition (app.services.subscription_service).

The webhook-activation test exercises deliberately-dormant code: nothing
creates a new SubscriptionPayment any more (self-checkout is retired), but
app.services.payment_service's shared Razorpay webhook dispatcher still
calls subscription_service.try_activate_by_provider_order_id for anything
that might still be in flight from before that change, so a pre-existing
PENDING row must still resolve correctly if a webhook for it ever arrives.
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
    assert body["plan_name"] is None
    assert body["amount"] is None
    assert body["subscription_id"] is None
    assert body["current_period_start"] is None


def test_subscription_view_requires_owner_role(client, db_session):
    owner = register_and_login(client, db_session, business_name="Sub Biz 2")

    for role in ["MANAGER", "CASH_COUNTER", "SERVICE_COUNTER", "KITCHEN"]:
        staff = _create_staff_and_login(client, owner["headers"], role)
        resp = client.get("/api/v1/subscription", headers=staff["headers"])
        assert resp.status_code == 403, f"{role} should not be able to view the subscription"


def test_unauthenticated_request_rejected(client):
    resp = client.get("/api/v1/subscription")
    assert resp.status_code == 401


def test_business_cannot_reach_platform_provisioning_routes(client, db_session):
    """The write side moved entirely to app.api.platform.subscriptions,
    behind a platform token — a business's own owner token must not work
    there at all."""
    owner = register_and_login(client, db_session, business_name="Sub Biz 3")

    resp = client.post(
        f"/api/v1/platform/businesses/{owner['business_id']}/subscription/provision",
        json={"plan_name": "POS Only", "amount": 600, "billing_interval": "monthly", "months": 1},
        headers=owner["headers"],
    )
    assert resp.status_code == 401


def _seed_pending_payment(db_session, business_id, *, provider_order_id="order_test_123"):
    subscription = Subscription(
        business_id=business_id, plan_name="POS Only", amount=600.0,
        currency="INR", billing_interval="monthly", status=SubscriptionStatus.PENDING,
    )
    db_session.add(subscription)
    db_session.flush()
    now = datetime.now(timezone.utc)
    payment = SubscriptionPayment(
        business_id=business_id, subscription_id=subscription.id, status=PaymentStatus.PENDING,
        amount=600.0, currency="INR", provider="RAZORPAY",
        provider_order_id=provider_order_id, period_start=now, period_end=now + timedelta(days=30),
    )
    db_session.add(payment)
    db_session.flush()
    return subscription, payment


def test_get_subscription_is_tenant_isolated(client, db_session):
    owner_a = register_and_login(client, db_session, business_name="Sub Biz 8a")
    owner_b = register_and_login(client, db_session, business_name="Sub Biz 8b")
    business_a_id = uuid.UUID(owner_a["business_id"])
    _seed_pending_payment(db_session, business_a_id, provider_order_id="order_iso_test")
    db_session.commit()

    resp = client.get("/api/v1/subscription", headers=owner_b["headers"])
    assert resp.json()["status"] == "NOT_CONFIGURED"


def test_active_subscription_lazily_reports_grace_then_suspended(client, db_session):
    owner = register_and_login(client, db_session, business_name="Sub Biz 9")
    business_id = uuid.UUID(owner["business_id"])

    just_lapsed = datetime.now(timezone.utc) - timedelta(hours=1)
    subscription = Subscription(
        business_id=business_id, plan_name="POS Only", amount=600.0, currency="INR", billing_interval="monthly",
        status=SubscriptionStatus.ACTIVE, current_period_start=just_lapsed - timedelta(days=30),
        current_period_end=just_lapsed,
    )
    db_session.add(subscription)
    db_session.commit()

    # An hour past current_period_end: within the 3-day grace window.
    resp = client.get("/api/v1/subscription", headers=owner["headers"])
    assert resp.status_code == 200
    assert resp.json()["status"] == "GRACE"

    # Push it well past the grace window and re-read.
    subscription.current_period_end = datetime.now(timezone.utc) - timedelta(
        days=subscription_service.GRACE_PERIOD_DAYS + 1
    )
    db_session.commit()

    resp = client.get("/api/v1/subscription", headers=owner["headers"])
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUSPENDED"


def test_webhook_activates_a_still_pending_subscription_payment(client, db_session, platform_razorpay):
    """Dormant-path coverage — see module docstring."""
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
