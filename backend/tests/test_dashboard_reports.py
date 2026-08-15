from tests.helpers import create_category_and_item, create_table, register_and_login


def test_dashboard_reflects_real_orders(client, db_session):
    owner = register_and_login(client, db_session, business_name="Dashboard Biz 1")
    _, item = create_category_and_item(client, owner["headers"], price=50)
    table = create_table(client, owner["headers"])

    resp = client.get("/api/v1/dashboard", headers=owner["headers"])
    assert resp.status_code == 200
    before = resp.json()["orders_today"]

    client.post(
        "/api/v1/orders",
        json={
            "location_id": table["id"], "source": "DINE_IN", "pricing_context": "DINE_IN",
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
        },
        headers=owner["headers"],
    )

    resp = client.get("/api/v1/dashboard", headers=owner["headers"])
    assert resp.json()["orders_today"] == before + 1


def test_reports_channel_breakdown(client, db_session):
    owner = register_and_login(client, db_session, business_name="Dashboard Biz 2")
    _, item = create_category_and_item(client, owner["headers"], price=75)
    table = create_table(client, owner["headers"])

    client.post(
        "/api/v1/orders",
        json={
            "location_id": table["id"], "source": "DINE_IN", "pricing_context": "DINE_IN",
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
        },
        headers=owner["headers"],
    )

    resp = client.get("/api/v1/reports/channels", headers=owner["headers"])
    assert resp.status_code == 200
    channels = {c["channel"]: c for c in resp.json()}
    assert channels["DINE_IN"]["order_count"] >= 1
