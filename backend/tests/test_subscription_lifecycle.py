"""The platform-managed subscription lifecycle end-to-end: provision, renew
(including the "unused days carry forward" math), suspend, cancel, and —
the part that actually matters commercially — that a SUSPENDED business is
genuinely locked out of its own dashboard by app.main.SubscriptionGateMiddleware,
not just marked suspended in a column nobody reads.
"""
from datetime import datetime, timedelta, timezone

from app.models.enums import SubscriptionStatus
from app.models.subscription import Subscription
from tests.helpers import platform_login, register_and_login


def test_provisioning_a_plan_makes_it_active(client, db_session):
    owner = register_and_login(client, db_session, business_name="Plan Biz 1")
    platform_headers = platform_login(client, db_session)

    resp = client.post(
        f"/api/v1/platform/businesses/{owner['business_id']}/subscription/provision",
        json={"plan_name": "POS + QR", "amount": 850, "billing_interval": "monthly", "months": 1},
        headers=platform_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ACTIVE"
    assert body["plan_name"] == "POS + QR"
    assert body["amount"] == 850.0

    resp = client.get("/api/v1/subscription", headers=owner["headers"])
    assert resp.json()["status"] == "ACTIVE"


def test_renewing_before_expiry_adds_to_the_remaining_days_not_from_today(client, db_session):
    """Confirmed with the client: paying early must never lose the unused
    remainder of the current period."""
    owner = register_and_login(client, db_session, business_name="Plan Biz 2")
    platform_headers = platform_login(client, db_session)
    business_id = owner["business_id"]

    far_future = datetime.now(timezone.utc) + timedelta(days=20)
    subscription = Subscription(
        business_id=business_id, plan_name="POS Only", amount=600.0, currency="INR", billing_interval="monthly",
        status=SubscriptionStatus.ACTIVE,
        current_period_start=datetime.now(timezone.utc), current_period_end=far_future,
    )
    db_session.add(subscription)
    db_session.commit()

    resp = client.post(
        f"/api/v1/platform/businesses/{business_id}/subscription/renew",
        json={"months": 1}, headers=platform_headers,
    )
    assert resp.status_code == 200, resp.text
    new_end = datetime.fromisoformat(resp.json()["current_period_end"])

    # A month added to a period that already had 20 days left must land
    # roughly a month past that existing end date, not a month from today.
    assert new_end > far_future + timedelta(days=25)


def test_suspended_business_is_blocked_from_its_own_dashboard(client, db_session):
    owner = register_and_login(client, db_session, business_name="Plan Biz 3")
    platform_headers = platform_login(client, db_session)
    business_id = owner["business_id"]

    # Confirm the dashboard works before suspension.
    resp = client.get("/api/v1/orders", headers=owner["headers"])
    assert resp.status_code == 200

    resp = client.post(f"/api/v1/platform/businesses/{business_id}/subscription/provision",
                        json={"plan_name": "POS Only", "amount": 600, "billing_interval": "monthly", "months": 1},
                        headers=platform_headers)
    assert resp.status_code == 200
    resp = client.post(f"/api/v1/platform/businesses/{business_id}/subscription/suspend", headers=platform_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "SUSPENDED"

    # The gate: an ordinary dashboard route now 402s for this business.
    resp = client.get("/api/v1/orders", headers=owner["headers"])
    assert resp.status_code == 402


def test_grace_period_business_still_works(client, db_session):
    """Only SUSPENDED blocks the dashboard — GRACE is a warning, not a lock."""
    owner = register_and_login(client, db_session, business_name="Plan Biz 4")
    business_id = owner["business_id"]

    just_lapsed = datetime.now(timezone.utc) - timedelta(hours=2)
    subscription = Subscription(
        business_id=business_id, plan_name="POS Only", amount=600.0, currency="INR", billing_interval="monthly",
        status=SubscriptionStatus.ACTIVE,
        current_period_start=just_lapsed - timedelta(days=30), current_period_end=just_lapsed,
    )
    db_session.add(subscription)
    db_session.commit()

    resp = client.get("/api/v1/subscription", headers=owner["headers"])
    assert resp.json()["status"] == "GRACE"

    resp = client.get("/api/v1/orders", headers=owner["headers"])
    assert resp.status_code == 200


def test_renewing_a_suspended_business_reactivates_it_immediately(client, db_session):
    owner = register_and_login(client, db_session, business_name="Plan Biz 5")
    platform_headers = platform_login(client, db_session)
    business_id = owner["business_id"]

    long_expired = datetime.now(timezone.utc) - timedelta(days=30)
    subscription = Subscription(
        business_id=business_id, plan_name="POS Only", amount=600.0, currency="INR", billing_interval="monthly",
        status=SubscriptionStatus.SUSPENDED,
        current_period_start=long_expired - timedelta(days=30), current_period_end=long_expired,
    )
    db_session.add(subscription)
    db_session.commit()

    resp = client.get("/api/v1/orders", headers=owner["headers"])
    assert resp.status_code == 402

    resp = client.post(
        f"/api/v1/platform/businesses/{business_id}/subscription/renew",
        json={"months": 1}, headers=platform_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ACTIVE"
    # Reactivating from a long-expired period starts fresh from today, not
    # stacked a month past the old (long-past) end date.
    new_end = datetime.fromisoformat(resp.json()["current_period_end"])
    assert new_end > datetime.now(timezone.utc) + timedelta(days=25)

    resp = client.get("/api/v1/orders", headers=owner["headers"])
    assert resp.status_code == 200


def test_platform_login_itself_still_works_for_a_suspended_business_owner(client, db_session):
    """Login must never be gated — a suspended owner needs to be able to
    log in and see why (the subscription banner), even if nothing else
    works."""
    owner = register_and_login(client, db_session, business_name="Plan Biz 6")
    platform_headers = platform_login(client, db_session)
    business_id = owner["business_id"]

    client.post(f"/api/v1/platform/businesses/{business_id}/subscription/provision",
                json={"plan_name": "POS Only", "amount": 600, "billing_interval": "monthly", "months": 1},
                headers=platform_headers)
    client.post(f"/api/v1/platform/businesses/{business_id}/subscription/suspend", headers=platform_headers)

    resp = client.post(
        "/api/v1/auth/login", json={"identifier": owner["payload"]["email"], "password": owner["payload"]["password"]}
    )
    assert resp.status_code == 200, resp.text

    # The subscription view itself must also stay reachable, so the banner
    # can render.
    resp = client.get("/api/v1/subscription", headers=owner["headers"])
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUSPENDED"


def test_cancelling_a_plan_is_distinct_from_suspension(client, db_session):
    owner = register_and_login(client, db_session, business_name="Plan Biz 7")
    platform_headers = platform_login(client, db_session)
    business_id = owner["business_id"]

    client.post(f"/api/v1/platform/businesses/{business_id}/subscription/provision",
                json={"plan_name": "POS Only", "amount": 600, "billing_interval": "monthly", "months": 1},
                headers=platform_headers)

    resp = client.post(f"/api/v1/platform/businesses/{business_id}/subscription/cancel", headers=platform_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "CANCELLED"
    assert resp.json()["cancelled_at"] is not None

    # CANCELLED does not trip the SUSPENDED-only middleware gate — a
    # deliberately-ended relationship is not the same enforcement as a
    # billing lapse (see subscription_service.cancel_plan's docstring).
    resp = client.get("/api/v1/orders", headers=owner["headers"])
    assert resp.status_code == 200
