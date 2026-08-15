from tests.helpers import create_category_and_item, enable_feature, register_and_login


def _create_staff_and_login(client, owner_headers, role: str):
    import uuid

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


def _create_delivery_order(client, headers, item_id):
    resp = client.post(
        "/api/v1/orders",
        json={
            "location_id": None, "source": "DELIVERY", "pricing_context": "DELIVERY",
            "items": [{"menu_item_id": item_id, "quantity": 1}],
            "delivery_address": "221B Baker Street, Mumbai",
            "delivery_instructions": "Ring the bell twice",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_and_retrieve_delivery_order_exposes_address_and_status(client, db_session):
    owner = register_and_login(client, db_session, business_name="Delivery Biz 1")
    enable_feature(client, owner["headers"], "DELIVERY")
    _, item = create_category_and_item(client, owner["headers"])

    order = _create_delivery_order(client, owner["headers"], item["id"])
    assert order["delivery_address"] == "221B Baker Street, Mumbai"
    assert order["delivery_instructions"] == "Ring the bell twice"
    assert order["delivery_status"] == "PLACED"

    resp = client.get(f"/api/v1/orders/{order['id']}", headers=owner["headers"])
    assert resp.status_code == 200
    assert resp.json()["delivery_status"] == "PLACED"


def test_delivery_status_valid_transition_updates_order_status_too(client, db_session):
    owner = register_and_login(client, db_session, business_name="Delivery Biz 2")
    enable_feature(client, owner["headers"], "DELIVERY")
    _, item = create_category_and_item(client, owner["headers"])
    order = _create_delivery_order(client, owner["headers"], item["id"])

    resp = client.put(
        f"/api/v1/delivery/orders/{order['id']}/status", json={"status": "CONFIRMED"}, headers=owner["headers"]
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["delivery_status"] == "CONFIRMED"
    assert resp.json()["status"] == "CONFIRMED"  # staff/kitchen views must reflect live progress

    for next_status in ["PREPARING", "READY", "OUT_FOR_DELIVERY", "DELIVERED"]:
        resp = client.put(
            f"/api/v1/delivery/orders/{order['id']}/status", json={"status": next_status}, headers=owner["headers"]
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["delivery_status"] == next_status
        assert resp.json()["status"] == next_status


def test_delivery_status_invalid_transition_rejected(client, db_session):
    owner = register_and_login(client, db_session, business_name="Delivery Biz 3")
    enable_feature(client, owner["headers"], "DELIVERY")
    _, item = create_category_and_item(client, owner["headers"])
    order = _create_delivery_order(client, owner["headers"], item["id"])

    # PLACED -> DELIVERED (skipping the whole lifecycle) must be rejected.
    resp = client.put(
        f"/api/v1/delivery/orders/{order['id']}/status", json={"status": "DELIVERED"}, headers=owner["headers"]
    )
    assert resp.status_code == 400

    # READY -> then DELIVERED -> PREPARING must be rejected (terminal state).
    for step in ["CONFIRMED", "PREPARING", "READY", "OUT_FOR_DELIVERY", "DELIVERED"]:
        resp = client.put(
            f"/api/v1/delivery/orders/{order['id']}/status", json={"status": step}, headers=owner["headers"]
        )
        assert resp.status_code == 200, resp.text

    resp = client.put(
        f"/api/v1/delivery/orders/{order['id']}/status", json={"status": "PREPARING"}, headers=owner["headers"]
    )
    assert resp.status_code == 400


def test_delivery_status_requires_delivery_role(client, db_session):
    owner = register_and_login(client, db_session, business_name="Delivery Biz 4")
    enable_feature(client, owner["headers"], "DELIVERY")
    _, item = create_category_and_item(client, owner["headers"])
    order = _create_delivery_order(client, owner["headers"], item["id"])

    cash_counter = _create_staff_and_login(client, owner["headers"], "CASH_COUNTER")
    resp = client.put(
        f"/api/v1/delivery/orders/{order['id']}/status", json={"status": "CONFIRMED"}, headers=cash_counter["headers"]
    )
    assert resp.status_code == 403

    delivery_staff = _create_staff_and_login(client, owner["headers"], "DELIVERY")
    resp = client.put(
        f"/api/v1/delivery/orders/{order['id']}/status", json={"status": "CONFIRMED"}, headers=delivery_staff["headers"]
    )
    assert resp.status_code == 200


def test_delivery_status_blocked_when_feature_flag_off(client, db_session):
    owner = register_and_login(client, db_session, business_name="Delivery Biz 5")
    enable_feature(client, owner["headers"], "DELIVERY")
    _, item = create_category_and_item(client, owner["headers"])
    order = _create_delivery_order(client, owner["headers"], item["id"])

    # Disable it again after creating the order.
    resp = client.put("/api/v1/settings/features/DELIVERY", json={"enabled": False}, headers=owner["headers"])
    assert resp.status_code == 200

    resp = client.put(
        f"/api/v1/delivery/orders/{order['id']}/status", json={"status": "CONFIRMED"}, headers=owner["headers"]
    )
    assert resp.status_code == 403


def test_delivery_orders_are_tenant_isolated(client, db_session):
    owner_a = register_and_login(client, db_session, business_name="Delivery Biz 6a")
    owner_b = register_and_login(client, db_session, business_name="Delivery Biz 6b")
    enable_feature(client, owner_a["headers"], "DELIVERY")
    enable_feature(client, owner_b["headers"], "DELIVERY")
    _, item_a = create_category_and_item(client, owner_a["headers"])
    order_a = _create_delivery_order(client, owner_a["headers"], item_a["id"])

    resp = client.put(
        f"/api/v1/delivery/orders/{order_a['id']}/status", json={"status": "CONFIRMED"}, headers=owner_b["headers"]
    )
    assert resp.status_code == 404

    resp = client.get("/api/v1/delivery/orders", headers=owner_b["headers"])
    assert resp.status_code == 200
    assert all(o["id"] != order_a["id"] for o in resp.json())


def test_non_delivery_order_rejects_delivery_status_update(client, db_session):
    owner = register_and_login(client, db_session, business_name="Delivery Biz 7")
    enable_feature(client, owner["headers"], "DELIVERY")
    _, item = create_category_and_item(client, owner["headers"])
    table = client.post(
        "/api/v1/tables", json={"location_type": "TABLE", "name": "T1"}, headers=owner["headers"]
    ).json()
    resp = client.post(
        "/api/v1/orders",
        json={
            "location_id": table["id"], "source": "DINE_IN", "pricing_context": "DINE_IN",
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
        },
        headers=owner["headers"],
    )
    dine_in_order = resp.json()

    resp = client.put(
        f"/api/v1/delivery/orders/{dine_in_order['id']}/status", json={"status": "CONFIRMED"}, headers=owner["headers"]
    )
    assert resp.status_code == 400
