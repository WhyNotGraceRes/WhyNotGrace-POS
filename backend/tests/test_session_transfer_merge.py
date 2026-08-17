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


def test_transfer_session_moves_orders_and_swaps_table_status(client, db_session):
    owner = register_and_login(client, db_session, business_name="Transfer Biz 1")
    _, item = create_category_and_item(client, owner["headers"], price=100)
    table_a = create_table(client, owner["headers"], name="A1")
    table_b = create_table(client, owner["headers"], name="A2")

    order = _place_order(client, owner["headers"], table_a, item)

    resp = client.post(
        f"/api/v1/orders/sessions/{order['session_id']}/transfer",
        json={"location_id": table_b["id"]},
        headers=owner["headers"],
    )
    assert resp.status_code == 200, resp.text
    orders = resp.json()
    assert len(orders) == 1
    assert orders[0]["location_id"] == table_b["id"]

    resp = client.get(f"/api/v1/orders/{order['id']}", headers=owner["headers"])
    assert resp.json()["location_id"] == table_b["id"]

    locations = {loc["id"]: loc for loc in client.get("/api/v1/tables", headers=owner["headers"]).json()}
    assert locations[table_a["id"]]["status"] == "AVAILABLE"
    assert locations[table_b["id"]]["status"] != "AVAILABLE"


def test_transfer_rejects_occupied_destination(client, db_session):
    owner = register_and_login(client, db_session, business_name="Transfer Biz 2")
    _, item = create_category_and_item(client, owner["headers"], price=100)
    table_a = create_table(client, owner["headers"], name="B1")
    table_b = create_table(client, owner["headers"], name="B2")

    order_a = _place_order(client, owner["headers"], table_a, item)
    _place_order(client, owner["headers"], table_b, item)  # occupies table_b

    resp = client.post(
        f"/api/v1/orders/sessions/{order_a['session_id']}/transfer",
        json={"location_id": table_b["id"]},
        headers=owner["headers"],
    )
    assert resp.status_code == 400
    assert "not available" in resp.json()["detail"]


def test_transfer_rejected_once_bill_started(client, db_session):
    owner = register_and_login(client, db_session, business_name="Transfer Biz 3")
    _, item = create_category_and_item(client, owner["headers"], price=100)
    table_a = create_table(client, owner["headers"], name="C1")
    table_b = create_table(client, owner["headers"], name="C2")
    order = _place_order(client, owner["headers"], table_a, item)

    client.post(
        "/api/v1/billing/generate",
        json={"session_id": order["session_id"], "use_default_tax": False, "use_default_service_charge": False},
        headers=owner["headers"],
    )

    resp = client.post(
        f"/api/v1/orders/sessions/{order['session_id']}/transfer",
        json={"location_id": table_b["id"]},
        headers=owner["headers"],
    )
    assert resp.status_code == 400
    assert "bill" in resp.json()["detail"].lower()


def test_merge_sessions_combines_orders_and_frees_losing_table(client, db_session):
    owner = register_and_login(client, db_session, business_name="Merge Biz 1")
    _, item = create_category_and_item(client, owner["headers"], price=100)
    table_a = create_table(client, owner["headers"], name="D1")
    table_b = create_table(client, owner["headers"], name="D2")

    order_a = _place_order(client, owner["headers"], table_a, item)
    order_b = _place_order(client, owner["headers"], table_b, item)

    resp = client.post(
        f"/api/v1/orders/sessions/{order_b['session_id']}/merge",
        json={"into_session_id": order_a["session_id"]},
        headers=owner["headers"],
    )
    assert resp.status_code == 200, resp.text
    orders = resp.json()
    assert len(orders) == 2
    assert all(o["session_id"] == order_a["session_id"] for o in orders)
    assert all(o["location_id"] == table_a["id"] for o in orders)

    locations = {loc["id"]: loc for loc in client.get("/api/v1/tables", headers=owner["headers"]).json()}
    assert locations[table_b["id"]]["status"] == "AVAILABLE"

    # The losing session must never accept another order — merged sessions
    # are retired for real (see order_service.merge_sessions).
    resp = client.get(f"/api/v1/orders/{order_b['id']}", headers=owner["headers"])
    assert resp.json()["session_id"] == order_a["session_id"]


def test_merge_into_itself_rejected(client, db_session):
    owner = register_and_login(client, db_session, business_name="Merge Biz 2")
    _, item = create_category_and_item(client, owner["headers"], price=100)
    table = create_table(client, owner["headers"])
    order = _place_order(client, owner["headers"], table, item)

    resp = client.post(
        f"/api/v1/orders/sessions/{order['session_id']}/merge",
        json={"into_session_id": order["session_id"]},
        headers=owner["headers"],
    )
    assert resp.status_code == 400


def test_merge_rejected_once_either_side_has_a_bill(client, db_session):
    owner = register_and_login(client, db_session, business_name="Merge Biz 3")
    _, item = create_category_and_item(client, owner["headers"], price=100)
    table_a = create_table(client, owner["headers"], name="E1")
    table_b = create_table(client, owner["headers"], name="E2")
    order_a = _place_order(client, owner["headers"], table_a, item)
    order_b = _place_order(client, owner["headers"], table_b, item)

    client.post(
        "/api/v1/billing/generate",
        json={"session_id": order_a["session_id"], "use_default_tax": False, "use_default_service_charge": False},
        headers=owner["headers"],
    )

    resp = client.post(
        f"/api/v1/orders/sessions/{order_b['session_id']}/merge",
        json={"into_session_id": order_a["session_id"]},
        headers=owner["headers"],
    )
    assert resp.status_code == 400
    assert "bill" in resp.json()["detail"].lower()
