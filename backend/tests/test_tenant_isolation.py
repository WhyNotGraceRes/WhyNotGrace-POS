"""THE MOST IMPORTANT TEST SUITE: Business A must never be able to read,
modify, or enumerate Business B's data, regardless of whether B's
resource ids are guessed, brute-forced, or otherwise obtained. business_id
must always come from the authenticated user's JWT — never a client-
supplied value.
"""
from tests.helpers import create_category_and_item, create_table, enable_feature, register_and_login


def test_menu_items_are_isolated_between_businesses(client, db_session):
    biz_a = register_and_login(client, db_session, business_name="Tenant A Restaurant")
    biz_b = register_and_login(client, db_session, business_name="Tenant B Restaurant")

    _, item_a = create_category_and_item(client, biz_a["headers"])

    # B cannot see A's item in its own item list.
    resp = client.get("/api/v1/menu/items", headers=biz_b["headers"])
    assert resp.status_code == 200
    assert all(i["id"] != item_a["id"] for i in resp.json())

    # B cannot fetch A's item directly by id — must be a clean 404, not a
    # leak of A's data and not a 403 that would confirm the id exists.
    resp = client.get(f"/api/v1/menu/items/{item_a['id']}", headers=biz_b["headers"])
    assert resp.status_code == 404

    # B cannot modify A's item.
    resp = client.put(f"/api/v1/menu/items/{item_a['id']}", json={"name": "Hacked"}, headers=biz_b["headers"])
    assert resp.status_code == 404

    # B cannot delete A's item.
    resp = client.delete(f"/api/v1/menu/items/{item_a['id']}", headers=biz_b["headers"])
    assert resp.status_code == 404


def test_tables_and_locations_are_isolated(client, db_session):
    biz_a = register_and_login(client, db_session, business_name="Tenant A Hotel")
    biz_b = register_and_login(client, db_session, business_name="Tenant B Hotel")

    table_a = create_table(client, biz_a["headers"], name="A1")

    resp = client.get("/api/v1/tables", headers=biz_b["headers"])
    assert all(t["id"] != table_a["id"] for t in resp.json())

    resp = client.put(f"/api/v1/locations/{table_a['id']}", json={"name": "Stolen"}, headers=biz_b["headers"])
    assert resp.status_code == 404


def test_orders_are_isolated(client, db_session):
    biz_a = register_and_login(client, db_session, business_name="Tenant A Orders")
    biz_b = register_and_login(client, db_session, business_name="Tenant B Orders")

    _, item_a = create_category_and_item(client, biz_a["headers"])
    table_a = create_table(client, biz_a["headers"])

    resp = client.post(
        "/api/v1/orders",
        json={
            "location_id": table_a["id"],
            "source": "DINE_IN",
            "pricing_context": "DINE_IN",
            "items": [{"menu_item_id": item_a["id"], "quantity": 1}],
        },
        headers=biz_a["headers"],
    )
    assert resp.status_code == 201, resp.text
    order_a = resp.json()

    # B cannot see A's order in its list.
    resp = client.get("/api/v1/orders", headers=biz_b["headers"])
    assert all(o["id"] != order_a["id"] for o in resp.json())

    # B cannot fetch A's order directly.
    resp = client.get(f"/api/v1/orders/{order_a['id']}", headers=biz_b["headers"])
    assert resp.status_code == 404

    # B cannot cancel A's order.
    resp = client.post(f"/api/v1/orders/{order_a['id']}/cancel", headers=biz_b["headers"])
    assert resp.status_code == 404


def test_staff_list_is_isolated(client, db_session):
    biz_a = register_and_login(client, db_session, business_name="Tenant A Staff")
    biz_b = register_and_login(client, db_session, business_name="Tenant B Staff")

    resp = client.get("/api/v1/staff", headers=biz_b["headers"])
    staff_b_ids = {s["id"] for s in resp.json()}
    assert biz_a["user_id"] not in staff_b_ids


def test_feature_flags_are_isolated(client, db_session):
    biz_a = register_and_login(client, db_session, business_name="Tenant A Flags")
    biz_b = register_and_login(client, db_session, business_name="Tenant B Flags")

    enable_feature(client, db_session, biz_a, "DELIVERY")

    resp = client.get("/api/v1/settings/features", headers=biz_b["headers"])
    flags = {f["module"]: f["enabled"] for f in resp.json()}
    assert flags["DELIVERY"] is False  # B's flags are unaffected by A's change


def test_customers_are_isolated(client, db_session):
    biz_a = register_and_login(client, db_session, business_name="Tenant A Customers")
    biz_b = register_and_login(client, db_session, business_name="Tenant B Customers")

    resp = client.post(
        "/api/v1/customers", json={"first_name": "Alice", "mobile": "9000000001"}, headers=biz_a["headers"]
    )
    assert resp.status_code == 201
    customer_a = resp.json()

    resp = client.get("/api/v1/customers", headers=biz_b["headers"])
    assert all(c["id"] != customer_a["id"] for c in resp.json())

    resp = client.put(f"/api/v1/customers/{customer_a['id']}", json={"first_name": "Hacked"}, headers=biz_b["headers"])
    assert resp.status_code == 404


def test_audit_logs_are_isolated(client, db_session):
    biz_a = register_and_login(client, db_session, business_name="Tenant A Audit")
    biz_b = register_and_login(client, db_session, business_name="Tenant B Audit")

    create_category_and_item(client, biz_a["headers"])

    resp = client.get("/api/v1/admin/audit-logs", headers=biz_b["headers"])
    assert resp.status_code == 200
    for log in resp.json():
        assert "Tenant A" not in (log.get("metadata_json") or "")
