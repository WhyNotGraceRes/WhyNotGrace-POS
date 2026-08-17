"""End-to-end dine-in flow: order -> KOT -> kitchen -> service -> bill ->
additional order -> cash payment -> bill paid.
"""
from tests.helpers import create_category_and_item, create_table, register_and_login


def _place_order(client, headers, table, item, qty=1):
    resp = client.post(
        "/api/v1/orders",
        json={
            "location_id": table["id"], "source": "DINE_IN", "pricing_context": "DINE_IN",
            "items": [{"menu_item_id": item["id"], "quantity": qty}],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_additional_order_only_sends_new_items_to_kitchen(client, db_session):
    owner = register_and_login(client, db_session, business_name="Flow Biz 1")
    _, item = create_category_and_item(client, owner["headers"], price=100)
    table = create_table(client, owner["headers"])

    order1 = _place_order(client, owner["headers"], table, item, qty=2)
    assert order1["is_additional"] is False

    order2 = _place_order(client, owner["headers"], table, item, qty=1)
    assert order2["is_additional"] is True
    assert order2["session_id"] == order1["session_id"]

    resp = client.get("/api/v1/kot", headers=owner["headers"])
    kots = resp.json()
    kots_for_order1 = [k for k in kots if k["order_id"] == order1["id"]]
    kots_for_order2 = [k for k in kots if k["order_id"] == order2["id"]]
    assert len(kots_for_order1) == 1
    assert len(kots_for_order2) == 1
    assert kots_for_order1[0]["items"][0]["quantity"] == 2
    assert kots_for_order2[0]["items"][0]["quantity"] == 1


def test_active_only_filter_excludes_served_orders(client, db_session):
    owner = register_and_login(client, db_session, business_name="Flow Biz Active Only")
    _, item = create_category_and_item(client, owner["headers"])
    table1 = create_table(client, owner["headers"])
    table2 = create_table(client, owner["headers"])

    active_order = _place_order(client, owner["headers"], table1, item)
    served_order = _place_order(client, owner["headers"], table2, item)

    served_kot = next(
        k for k in client.get("/api/v1/kot", headers=owner["headers"]).json() if k["order_id"] == served_order["id"]
    )
    for target in ("ACCEPTED", "PREPARING", "READY"):
        client.put(f"/api/v1/kot/{served_kot['id']}/status", json={"status": target}, headers=owner["headers"])
    resp = client.post(f"/api/v1/kitchen/service/{served_kot['id']}/serve", headers=owner["headers"])
    assert resp.status_code == 200
    assert resp.json()["status"] == "SERVED"

    resp = client.get("/api/v1/orders", params={"active_only": True}, headers=owner["headers"])
    assert resp.status_code == 200
    order_ids = {o["id"] for o in resp.json()}
    assert active_order["id"] in order_ids
    assert served_order["id"] not in order_ids


def test_kot_lifecycle_and_service_counter(client, db_session):
    owner = register_and_login(client, db_session, business_name="Flow Biz 2")
    _, item = create_category_and_item(client, owner["headers"])
    table = create_table(client, owner["headers"])
    order = _place_order(client, owner["headers"], table, item)

    kot = client.get("/api/v1/kot", headers=owner["headers"]).json()[0]

    for target in ("ACCEPTED", "PREPARING", "READY"):
        resp = client.put(f"/api/v1/kot/{kot['id']}/status", json={"status": target}, headers=owner["headers"])
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == target

    resp = client.get("/api/v1/kitchen/service/ready", headers=owner["headers"])
    assert any(k["id"] == kot["id"] for k in resp.json())

    resp = client.post(f"/api/v1/kitchen/service/{kot['id']}/serve", headers=owner["headers"])
    assert resp.status_code == 200
    assert resp.json()["status"] == "SERVED"

    order_resp = client.get(f"/api/v1/orders/{order['id']}", headers=owner["headers"])
    assert order_resp.json()["status"] == "SERVED"


def test_invalid_kot_status_transition_rejected(client, db_session):
    owner = register_and_login(client, db_session, business_name="Flow Biz 3")
    _, item = create_category_and_item(client, owner["headers"])
    table = create_table(client, owner["headers"])
    _place_order(client, owner["headers"], table, item)
    kot = client.get("/api/v1/kot", headers=owner["headers"]).json()[0]

    # NEW -> READY is not a legal jump
    resp = client.put(f"/api/v1/kot/{kot['id']}/status", json={"status": "READY"}, headers=owner["headers"])
    assert resp.status_code == 400


def test_billing_and_cash_payment_clears_table(client, db_session):
    owner = register_and_login(client, db_session, business_name="Flow Biz 4")
    _, item = create_category_and_item(client, owner["headers"], price=150)
    table = create_table(client, owner["headers"])
    order = _place_order(client, owner["headers"], table, item, qty=2)  # subtotal 300

    resp = client.post(
        "/api/v1/billing/generate", json={"session_id": order["session_id"], "use_default_tax": False, "use_default_service_charge": False},
        headers=owner["headers"],
    )
    assert resp.status_code == 201, resp.text
    bill = resp.json()
    assert bill["subtotal"] == 300.0
    assert bill["grand_total"] == 300.0
    assert bill["status"] == "OPEN"

    resp = client.post(
        "/api/v1/payments/cash", json={"bill_id": bill["id"], "amount": 300.0}, headers=owner["headers"]
    )
    assert resp.status_code == 201, resp.text

    resp = client.get(f"/api/v1/billing/{bill['id']}", headers=owner["headers"])
    assert resp.json()["status"] == "PAID"
    assert resp.json()["amount_paid"] == 300.0


def test_unbilled_orders_excludes_settled_sessions_but_shows_new_rounds(client, db_session):
    owner = register_and_login(client, db_session, business_name="Flow Biz Unbilled")
    _, item = create_category_and_item(client, owner["headers"], price=100)
    table1 = create_table(client, owner["headers"])
    table2 = create_table(client, owner["headers"])

    # Table 1: never billed — should show up as needing billing.
    open_order = _place_order(client, owner["headers"], table1, item)

    # Table 2: ordered, billed, and paid in full — should NOT show up.
    settled_order = _place_order(client, owner["headers"], table2, item)
    bill = client.post(
        "/api/v1/billing/generate",
        json={"session_id": settled_order["session_id"], "use_default_tax": False, "use_default_service_charge": False},
        headers=owner["headers"],
    ).json()
    client.post("/api/v1/payments/cash", json={"bill_id": bill["id"], "amount": 100.0}, headers=owner["headers"])

    resp = client.get("/api/v1/billing/unbilled-orders", headers=owner["headers"])
    assert resp.status_code == 200
    order_ids = {o["id"] for o in resp.json()}
    assert open_order["id"] in order_ids
    assert settled_order["id"] not in order_ids

    # A new round at the same table after settlement — same session_id
    # (OrderSession.is_closed is never written, see billing_service.py) —
    # must still surface as needing billing, without resurfacing the
    # already-paid order from before.
    new_round_order = _place_order(client, owner["headers"], table2, item)
    assert new_round_order["session_id"] == settled_order["session_id"]

    resp = client.get("/api/v1/billing/unbilled-orders", headers=owner["headers"])
    order_ids = {o["id"] for o in resp.json()}
    assert new_round_order["id"] in order_ids
    assert settled_order["id"] not in order_ids
    assert open_order["id"] in order_ids


def test_discount_reduces_grand_total(client, db_session):
    owner = register_and_login(client, db_session, business_name="Flow Biz 5")
    _, item = create_category_and_item(client, owner["headers"], price=100)
    table = create_table(client, owner["headers"])
    order = _place_order(client, owner["headers"], table, item, qty=1)

    bill = client.post(
        "/api/v1/billing/generate", json={"session_id": order["session_id"], "use_default_tax": False, "use_default_service_charge": False},
        headers=owner["headers"],
    ).json()

    resp = client.post(
        f"/api/v1/billing/{bill['id']}/discount",
        json={"name": "Loyalty discount", "amount": 10, "reason": "test"},
        headers=owner["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["grand_total"] == 90.0
