from tests.helpers import create_category_and_item, register_and_login


def test_contextual_pricing_overrides_base_price(client, db_session):
    owner = register_and_login(client, db_session, business_name="Pricing Biz 1")
    _, item = create_category_and_item(client, owner["headers"], price=250)

    resp = client.post(
        "/api/v1/pricing/rules",
        json={"item_id": item["id"], "context": "DELIVERY", "price": 280},
        headers=owner["headers"],
    )
    assert resp.status_code == 201

    table_resp = client.post(
        "/api/v1/tables", json={"location_type": "TABLE", "name": "T5"}, headers=owner["headers"]
    )
    table = table_resp.json()

    # Dine-in uses base_price (no rule for DINE_IN context).
    resp = client.post(
        "/api/v1/orders",
        json={
            "location_id": table["id"], "source": "DINE_IN", "pricing_context": "DINE_IN",
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
        },
        headers=owner["headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["items"][0]["unit_price"] == 250.0

    # Delivery uses the price rule instead of base_price.
    resp = client.post(
        "/api/v1/orders",
        json={
            "location_id": None, "source": "PICKUP", "pricing_context": "DELIVERY",
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
        },
        headers=owner["headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["items"][0]["unit_price"] == 280.0


def test_option_price_deltas_are_added_server_side(client, db_session):
    owner = register_and_login(client, db_session, business_name="Pricing Biz 2")
    _, item = create_category_and_item(client, owner["headers"], price=200)

    resp = client.post(
        f"/api/v1/menu/items/{item['id']}/option-groups",
        json={
            "name": "Spice Level", "is_required": True, "allow_multiple": False,
            "options": [{"name": "Extra Spicy", "price_delta": 20}],
        },
        headers=owner["headers"],
    )
    assert resp.status_code == 201
    updated_item = resp.json()
    option_id = updated_item["option_groups"][0]["options"][0]["id"]

    table = client.post(
        "/api/v1/tables", json={"location_type": "TABLE", "name": "T6"}, headers=owner["headers"]
    ).json()

    resp = client.post(
        "/api/v1/orders",
        json={
            "location_id": table["id"], "source": "DINE_IN", "pricing_context": "DINE_IN",
            "items": [{"menu_item_id": item["id"], "quantity": 2, "option_ids": [option_id]}],
        },
        headers=owner["headers"],
    )
    assert resp.status_code == 201
    order_item = resp.json()["items"][0]
    assert order_item["unit_price"] == 220.0  # 200 base + 20 option
    assert order_item["line_total"] == 440.0  # x2 quantity


def test_client_cannot_override_price(client, db_session):
    """The order schema has no price field at all — this test documents
    that guarantee by asserting a price-like field is rejected/ignored."""
    owner = register_and_login(client, db_session, business_name="Pricing Biz 3")
    _, item = create_category_and_item(client, owner["headers"], price=99)
    table = client.post(
        "/api/v1/tables", json={"location_type": "TABLE", "name": "T7"}, headers=owner["headers"]
    ).json()

    resp = client.post(
        "/api/v1/orders",
        json={
            "location_id": table["id"], "source": "DINE_IN", "pricing_context": "DINE_IN",
            "items": [{"menu_item_id": item["id"], "quantity": 1, "unit_price": 1}],
        },
        headers=owner["headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["items"][0]["unit_price"] == 99.0  # ignored client-supplied price
