from tests.helpers import create_table, register_and_login


def _create_category(client, headers, name="Mains"):
    resp = client.post("/api/v1/categories", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_item(client, headers, category_id, *, stock_quantity=None, price=100):
    resp = client.post(
        "/api/v1/menu/items",
        json={
            "category_id": category_id, "name": "Limited Thali", "base_price": price,
            "is_veg": True, "stock_quantity": stock_quantity,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _place_order(client, headers, table, item, qty=1):
    return client.post(
        "/api/v1/orders",
        json={
            "location_id": table["id"], "source": "DINE_IN", "pricing_context": "DINE_IN",
            "items": [{"menu_item_id": item["id"], "quantity": qty}],
        },
        headers=headers,
    )


def test_untracked_item_has_no_stock_field_and_behaves_as_before(client, db_session):
    owner = register_and_login(client, db_session, business_name="Stock Biz Untracked")
    category = _create_category(client, owner["headers"])
    item = _create_item(client, owner["headers"], category["id"])
    assert item["stock_quantity"] is None
    table = create_table(client, owner["headers"])

    resp = _place_order(client, owner["headers"], table, item, qty=50)
    assert resp.status_code == 201, resp.text


def test_order_decrements_stock_and_auto_sold_out_at_zero(client, db_session):
    owner = register_and_login(client, db_session, business_name="Stock Biz Decrement")
    category = _create_category(client, owner["headers"])
    item = _create_item(client, owner["headers"], category["id"], stock_quantity=3)
    table = create_table(client, owner["headers"])

    resp = _place_order(client, owner["headers"], table, item, qty=2)
    assert resp.status_code == 201, resp.text

    resp = client.get(f"/api/v1/menu/items/{item['id']}", headers=owner["headers"])
    assert resp.json()["stock_quantity"] == 1
    assert resp.json()["is_sold_out"] is False

    resp = _place_order(client, owner["headers"], table, item, qty=1)
    assert resp.status_code == 201, resp.text

    resp = client.get(f"/api/v1/menu/items/{item['id']}", headers=owner["headers"])
    assert resp.json()["stock_quantity"] == 0
    assert resp.json()["is_sold_out"] is True


def test_order_exceeding_stock_is_rejected(client, db_session):
    owner = register_and_login(client, db_session, business_name="Stock Biz Reject")
    category = _create_category(client, owner["headers"])
    item = _create_item(client, owner["headers"], category["id"], stock_quantity=2)
    table = create_table(client, owner["headers"])

    resp = _place_order(client, owner["headers"], table, item, qty=5)
    assert resp.status_code == 400
    assert "2" in resp.json()["detail"]

    # Rejected order must not have partially decremented stock.
    resp = client.get(f"/api/v1/menu/items/{item['id']}", headers=owner["headers"])
    assert resp.json()["stock_quantity"] == 2


def test_restocking_clears_auto_sold_out(client, db_session):
    owner = register_and_login(client, db_session, business_name="Stock Biz Restock")
    category = _create_category(client, owner["headers"])
    item = _create_item(client, owner["headers"], category["id"], stock_quantity=1)
    table = create_table(client, owner["headers"])

    _place_order(client, owner["headers"], table, item, qty=1)
    resp = client.get(f"/api/v1/menu/items/{item['id']}", headers=owner["headers"])
    assert resp.json()["is_sold_out"] is True

    resp = client.put(
        f"/api/v1/menu/items/{item['id']}", json={"stock_quantity": 10}, headers=owner["headers"]
    )
    assert resp.status_code == 200
    assert resp.json()["stock_quantity"] == 10
    assert resp.json()["is_sold_out"] is False

    resp = _place_order(client, owner["headers"], table, item, qty=1)
    assert resp.status_code == 201, resp.text


def test_setting_stock_quantity_null_clears_tracking(client, db_session):
    owner = register_and_login(client, db_session, business_name="Stock Biz Clear")
    category = _create_category(client, owner["headers"])
    item = _create_item(client, owner["headers"], category["id"], stock_quantity=1)

    resp = client.put(
        f"/api/v1/menu/items/{item['id']}", json={"stock_quantity": None}, headers=owner["headers"]
    )
    assert resp.status_code == 200
    assert resp.json()["stock_quantity"] is None
