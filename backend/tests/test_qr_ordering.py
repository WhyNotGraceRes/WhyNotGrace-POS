from tests.helpers import create_category_and_item, create_table, enable_feature, register_and_login


def test_qr_scan_menu_and_order_flow(client, db_session):
    owner = register_and_login(client, db_session, business_name="QR Biz 1")
    enable_feature(client, owner["headers"], "QR_ORDERING")
    _, item = create_category_and_item(client, owner["headers"], price=120)
    table = create_table(client, owner["headers"], name="Q1")

    # Business slug is needed for the public scan endpoint.
    biz_resp = client.get("/api/v1/businesses/me", headers=owner["headers"])
    slug = biz_resp.json()["slug"]

    locations = client.get("/api/v1/locations", headers=owner["headers"]).json()
    location = next(l for l in locations if l["id"] == table["id"])
    qr_code = location["qr_url"].split("c=")[1]

    resp = client.get(f"/api/v1/qr/scan/{slug}/{table['id']}", params={"c": qr_code})
    assert resp.status_code == 200, resp.text
    session_token = resp.json()["session_token"]

    resp = client.get("/api/v1/qr/menu", headers={"X-QR-Session": session_token})
    assert resp.status_code == 200
    assert resp.json()["categories"][0]["items"][0]["price"] == 120.0

    resp = client.post(
        "/api/v1/qr/orders",
        json={"items": [{"menu_item_id": item["id"], "quantity": 1}]},
        headers={"X-QR-Session": session_token},
    )
    assert resp.status_code == 201, resp.text
    order = resp.json()
    assert order["source"] == "QR"

    resp = client.get(f"/api/v1/qr/orders/{order['id']}", headers={"X-QR-Session": session_token})
    assert resp.status_code == 200


def test_qr_scan_fails_with_wrong_code(client, db_session):
    owner = register_and_login(client, db_session, business_name="QR Biz 2")
    enable_feature(client, owner["headers"], "QR_ORDERING")
    table = create_table(client, owner["headers"], name="Q2")
    biz_resp = client.get("/api/v1/businesses/me", headers=owner["headers"])
    slug = biz_resp.json()["slug"]

    resp = client.get(f"/api/v1/qr/scan/{slug}/{table['id']}", params={"c": "wrong-code"})
    assert resp.status_code == 403


def test_qr_ordering_blocked_when_feature_disabled(client, db_session):
    owner = register_and_login(client, db_session, business_name="QR Biz 3")
    table = create_table(client, owner["headers"], name="Q3")
    biz_resp = client.get("/api/v1/businesses/me", headers=owner["headers"])
    slug = biz_resp.json()["slug"]
    locations = client.get("/api/v1/locations", headers=owner["headers"]).json()
    location = next(l for l in locations if l["id"] == table["id"])
    qr_code = location["qr_url"].split("c=")[1]

    resp = client.get(f"/api/v1/qr/scan/{slug}/{table['id']}", params={"c": qr_code})
    assert resp.status_code == 403
