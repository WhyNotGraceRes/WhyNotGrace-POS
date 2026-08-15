from tests.helpers import create_category_and_item, register_and_login


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


def _add_variant(client, headers, item_id, name="Half", price_delta=0):
    resp = client.post(
        f"/api/v1/menu/items/{item_id}/variants",
        json={"name": name, "price_delta": price_delta}, headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["variants"][-1]


def _add_option_group_with_option(client, headers, item_id):
    resp = client.post(
        f"/api/v1/menu/items/{item_id}/option-groups",
        json={"name": "Spice", "options": [{"name": "Mild", "price_delta": 0}]},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    group = resp.json()["option_groups"][-1]
    return group, group["options"][-1]


def test_variant_update_and_delete(client, db_session):
    owner = register_and_login(client, db_session, business_name="MenuCrud Biz 1")
    _, item = create_category_and_item(client, owner["headers"])
    variant = _add_variant(client, owner["headers"], item["id"])

    resp = client.put(
        f"/api/v1/menu/variants/{variant['id']}", json={"name": "Full", "price_delta": 50}, headers=owner["headers"]
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Full"
    assert resp.json()["price_delta"] == 50.0

    resp = client.delete(f"/api/v1/menu/variants/{variant['id']}", headers=owner["headers"])
    assert resp.status_code == 204

    resp = client.put(
        f"/api/v1/menu/variants/{variant['id']}", json={"name": "Ghost"}, headers=owner["headers"]
    )
    assert resp.status_code == 404


def test_option_group_update_and_delete(client, db_session):
    owner = register_and_login(client, db_session, business_name="MenuCrud Biz 2")
    _, item = create_category_and_item(client, owner["headers"])
    group, _option = _add_option_group_with_option(client, owner["headers"], item["id"])

    resp = client.put(
        f"/api/v1/menu/option-groups/{group['id']}",
        json={"is_active": False, "is_required": True}, headers=owner["headers"],
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_active"] is False
    assert resp.json()["is_required"] is True

    resp = client.delete(f"/api/v1/menu/option-groups/{group['id']}", headers=owner["headers"])
    assert resp.status_code == 204

    resp = client.delete(f"/api/v1/menu/option-groups/{group['id']}", headers=owner["headers"])
    assert resp.status_code == 404


def test_option_update_and_delete(client, db_session):
    owner = register_and_login(client, db_session, business_name="MenuCrud Biz 3")
    _, item = create_category_and_item(client, owner["headers"])
    _group, option = _add_option_group_with_option(client, owner["headers"], item["id"])

    resp = client.put(
        f"/api/v1/menu/options/{option['id']}", json={"price_delta": 15}, headers=owner["headers"]
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["price_delta"] == 15.0

    resp = client.delete(f"/api/v1/menu/options/{option['id']}", headers=owner["headers"])
    assert resp.status_code == 204


def test_cannot_delete_variant_referenced_by_historical_order(client, db_session):
    """Deleting a variant used by a real order must fail with 409, and the
    historical order's data must remain completely unchanged afterward."""
    owner = register_and_login(client, db_session, business_name="MenuCrud Biz 4")
    _, item = create_category_and_item(client, owner["headers"], price=100)
    variant = _add_variant(client, owner["headers"], item["id"], name="Full", price_delta=50)

    table = client.post(
        "/api/v1/tables", json={"location_type": "TABLE", "name": "T1"}, headers=owner["headers"]
    ).json()
    resp = client.post(
        "/api/v1/orders",
        json={
            "location_id": table["id"], "source": "DINE_IN", "pricing_context": "DINE_IN",
            "items": [{"menu_item_id": item["id"], "variant_id": variant["id"], "quantity": 1}],
        },
        headers=owner["headers"],
    )
    assert resp.status_code == 201, resp.text
    order_id = resp.json()["id"]

    resp = client.delete(f"/api/v1/menu/variants/{variant['id']}", headers=owner["headers"])
    assert resp.status_code == 409, resp.text

    # Historical order snapshot must be untouched by the failed delete attempt.
    resp = client.get(f"/api/v1/orders/{order_id}", headers=owner["headers"])
    assert resp.status_code == 200
    assert resp.json()["items"][0]["unit_price"] == 150.0
    assert resp.json()["items"][0]["variant_id"] == variant["id"]

    # Deactivating instead of deleting must still work as the safe alternative.
    resp = client.put(
        f"/api/v1/menu/variants/{variant['id']}", json={"is_active": False}, headers=owner["headers"]
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_menu_variant_crud_requires_operational_role(client, db_session):
    owner = register_and_login(client, db_session, business_name="MenuCrud Biz 5")
    _, item = create_category_and_item(client, owner["headers"])
    variant = _add_variant(client, owner["headers"], item["id"])
    kitchen = _create_staff_and_login(client, owner["headers"], "KITCHEN")

    resp = client.put(
        f"/api/v1/menu/variants/{variant['id']}", json={"name": "Nope"}, headers=kitchen["headers"]
    )
    assert resp.status_code == 403

    resp = client.delete(f"/api/v1/menu/variants/{variant['id']}", headers=kitchen["headers"])
    assert resp.status_code == 403


def test_menu_crud_is_tenant_isolated(client, db_session):
    owner_a = register_and_login(client, db_session, business_name="MenuCrud Biz 6a")
    owner_b = register_and_login(client, db_session, business_name="MenuCrud Biz 6b")
    _, item_a = create_category_and_item(client, owner_a["headers"])
    variant_a = _add_variant(client, owner_a["headers"], item_a["id"])
    _, option_a = _add_option_group_with_option(client, owner_a["headers"], item_a["id"])

    resp = client.put(
        f"/api/v1/menu/variants/{variant_a['id']}", json={"name": "Hacked"}, headers=owner_b["headers"]
    )
    assert resp.status_code == 404

    resp = client.delete(f"/api/v1/menu/variants/{variant_a['id']}", headers=owner_b["headers"])
    assert resp.status_code == 404

    resp = client.put(
        f"/api/v1/menu/options/{option_a['id']}", json={"price_delta": 999}, headers=owner_b["headers"]
    )
    assert resp.status_code == 404
