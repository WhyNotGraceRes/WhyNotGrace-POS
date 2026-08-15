"""Real end-to-end verification of the loyalty earn -> redeem lifecycle,
per WHYNOTGRACE POS Phase 6 Foundation Patch Part 6: a genuinely earned
reward (created by loyalty_service.process_paid_bill firing off a real
paid bill, exactly as production does), redeemed once successfully, and
rejected on a second attempt. No reward row is ever inserted directly.
"""
import uuid

from tests.helpers import create_category_and_item, enable_feature, register_and_login


def _create_customer(client, headers, mobile=None):
    resp = client.post(
        "/api/v1/customers",
        json={"first_name": "Loyal Larry", "mobile": mobile or f"9{uuid.uuid4().int % 10**9:09d}"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_rule(client, headers, *, threshold=1, rule_type="ORDER_COUNT_THRESHOLD", reward_type="FREE_ITEM"):
    resp = client.post(
        "/api/v1/loyalty/rules",
        json={
            "name": "Every order is a winner", "rule_type": rule_type, "threshold": threshold,
            "reward_type": reward_type, "reward_value": None,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _place_and_pay_order(client, headers, *, item_id, customer_id, table_id):
    resp = client.post(
        "/api/v1/orders",
        json={
            "location_id": table_id, "source": "DINE_IN", "pricing_context": "DINE_IN",
            "customer_id": customer_id,
            "items": [{"menu_item_id": item_id, "quantity": 1}],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    order = resp.json()

    resp = client.post("/api/v1/billing/generate", json={"session_id": order["session_id"]}, headers=headers)
    assert resp.status_code == 201, resp.text
    bill = resp.json()

    resp = client.post(
        "/api/v1/payments/cash",
        json={"bill_id": bill["id"], "amount": bill["grand_total"], "method": "CASH"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return order, bill


def test_real_loyalty_earn_and_redeem_lifecycle(client, db_session):
    owner = register_and_login(client, db_session, business_name="Loyalty E2E Biz 1")
    enable_feature(client, owner["headers"], "LOYALTY")
    _, item = create_category_and_item(client, owner["headers"], price=500)
    customer = _create_customer(client, owner["headers"])
    rule = _create_rule(client, owner["headers"], threshold=1)
    table = client.post(
        "/api/v1/tables", json={"location_type": "TABLE", "name": "T1"}, headers=owner["headers"]
    ).json()

    # No account exists yet — nothing has been earned.
    resp = client.get(f"/api/v1/loyalty/accounts/{customer['id']}", headers=owner["headers"])
    assert resp.status_code == 404

    # Real order -> real bill -> real cash payment -> bill transitions PAID,
    # which is the one and only trigger loyalty_service listens for.
    _place_and_pay_order(client, owner["headers"], item_id=item["id"], customer_id=customer["id"], table_id=table["id"])

    resp = client.get(f"/api/v1/loyalty/accounts/{customer['id']}", headers=owner["headers"])
    assert resp.status_code == 200, resp.text
    account = resp.json()
    assert account["total_orders"] == 1
    assert account["total_spend"] == 500.0

    resp = client.get(f"/api/v1/loyalty/accounts/{customer['id']}/rewards", headers=owner["headers"])
    assert resp.status_code == 200
    rewards = resp.json()
    assert len(rewards) == 1
    reward = rewards[0]
    assert reward["rule_id"] == rule["id"]
    assert reward["is_redeemed"] is False

    # First redemption must succeed and mark the reward consumed.
    resp = client.post(f"/api/v1/loyalty/rewards/{reward['id']}/redeem", json={}, headers=owner["headers"])
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_redeemed"] is True

    resp = client.get(f"/api/v1/loyalty/accounts/{customer['id']}/rewards", headers=owner["headers"])
    assert resp.json()[0]["is_redeemed"] is True

    # Second redemption of the SAME reward must be rejected — it was
    # genuinely consumed, not just flagged client-side.
    resp = client.post(f"/api/v1/loyalty/rewards/{reward['id']}/redeem", json={}, headers=owner["headers"])
    assert resp.status_code == 400
    assert "already redeemed" in resp.json()["detail"].lower()


def test_loyalty_second_qualifying_order_earns_a_second_independent_reward(client, db_session):
    owner = register_and_login(client, db_session, business_name="Loyalty E2E Biz 2")
    enable_feature(client, owner["headers"], "LOYALTY")
    _, item = create_category_and_item(client, owner["headers"], price=300)
    customer = _create_customer(client, owner["headers"])
    _create_rule(client, owner["headers"], threshold=1)
    table = client.post(
        "/api/v1/tables", json={"location_type": "TABLE", "name": "T2"}, headers=owner["headers"]
    ).json()

    _place_and_pay_order(client, owner["headers"], item_id=item["id"], customer_id=customer["id"], table_id=table["id"])
    _place_and_pay_order(client, owner["headers"], item_id=item["id"], customer_id=customer["id"], table_id=table["id"])

    resp = client.get(f"/api/v1/loyalty/accounts/{customer['id']}", headers=owner["headers"])
    assert resp.json()["total_orders"] == 2

    resp = client.get(f"/api/v1/loyalty/accounts/{customer['id']}/rewards", headers=owner["headers"])
    rewards = resp.json()
    assert len(rewards) == 2  # threshold=1 fires once per qualifying order
    assert all(r["is_redeemed"] is False for r in rewards)


def test_loyalty_redemption_is_tenant_isolated(client, db_session):
    owner_a = register_and_login(client, db_session, business_name="Loyalty E2E Biz 3a")
    owner_b = register_and_login(client, db_session, business_name="Loyalty E2E Biz 3b")
    enable_feature(client, owner_a["headers"], "LOYALTY")
    enable_feature(client, owner_b["headers"], "LOYALTY")
    _, item_a = create_category_and_item(client, owner_a["headers"], price=400)
    customer_a = _create_customer(client, owner_a["headers"])
    _create_rule(client, owner_a["headers"], threshold=1)
    table_a = client.post(
        "/api/v1/tables", json={"location_type": "TABLE", "name": "T1"}, headers=owner_a["headers"]
    ).json()
    _place_and_pay_order(client, owner_a["headers"], item_id=item_a["id"], customer_id=customer_a["id"], table_id=table_a["id"])

    reward_a = client.get(f"/api/v1/loyalty/accounts/{customer_a['id']}/rewards", headers=owner_a["headers"]).json()[0]

    # Business B must not be able to see or redeem Business A's reward/account.
    resp = client.get(f"/api/v1/loyalty/accounts/{customer_a['id']}", headers=owner_b["headers"])
    assert resp.status_code == 404

    resp = client.post(f"/api/v1/loyalty/rewards/{reward_a['id']}/redeem", json={}, headers=owner_b["headers"])
    assert resp.status_code == 404

    # And it must still be genuinely redeemable back on Business A's side afterward.
    resp = client.post(f"/api/v1/loyalty/rewards/{reward_a['id']}/redeem", json={}, headers=owner_a["headers"])
    assert resp.status_code == 200
