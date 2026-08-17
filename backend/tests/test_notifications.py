from tests.helpers import create_category_and_item, create_table, enable_feature, register_and_login


def test_staff_placed_order_creates_no_notification(client, db_session):
    owner = register_and_login(client, db_session, business_name="Notify Biz Staff Order")
    _, item = create_category_and_item(client, owner["headers"], price=100)
    table = create_table(client, owner["headers"])

    client.post(
        "/api/v1/orders",
        json={
            "location_id": table["id"], "source": "DINE_IN", "pricing_context": "DINE_IN",
            "items": [{"menu_item_id": item["id"], "quantity": 1}],
        },
        headers=owner["headers"],
    )

    resp = client.get("/api/v1/notifications", headers=owner["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["unread_count"] == 0
    assert all(n["type"] != "NEW_CUSTOMER_ORDER" for n in data["notifications"])


def test_qr_order_creates_notification_and_can_be_read(client, db_session):
    owner = register_and_login(client, db_session, business_name="Notify Biz QR Order")
    enable_feature(client, db_session, owner, "QR_ORDERING")
    _, item = create_category_and_item(client, owner["headers"], price=120)
    table = create_table(client, owner["headers"], name="Q1")

    slug = client.get("/api/v1/businesses/me", headers=owner["headers"]).json()["slug"]
    locations = client.get("/api/v1/locations", headers=owner["headers"]).json()
    location = next(l for l in locations if l["id"] == table["id"])
    qr_code = location["qr_url"].split("c=")[1]

    scan = client.get(f"/api/v1/qr/scan/{slug}/{table['id']}", params={"c": qr_code})
    session_token = scan.json()["session_token"]

    order = client.post(
        "/api/v1/qr/orders",
        json={"items": [{"menu_item_id": item["id"], "quantity": 1}]},
        headers={"X-QR-Session": session_token},
    ).json()

    resp = client.get("/api/v1/notifications", headers=owner["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["unread_count"] >= 1
    matching = [n for n in data["notifications"] if n["type"] == "NEW_CUSTOMER_ORDER"]
    assert len(matching) == 1
    notification = matching[0]
    assert notification["is_read"] is False
    assert notification["resource_id"] == order["id"]
    assert order["order_number"] in notification["body"]

    resp = client.post(f"/api/v1/notifications/{notification['id']}/read", headers=owner["headers"])
    assert resp.status_code == 204

    resp = client.get("/api/v1/notifications", headers=owner["headers"])
    data = resp.json()
    matching = [n for n in data["notifications"] if n["type"] == "NEW_CUSTOMER_ORDER"]
    assert matching[0]["is_read"] is True


def test_mark_all_read_clears_unread_count(client, db_session):
    owner = register_and_login(client, db_session, business_name="Notify Biz Mark All")
    enable_feature(client, db_session, owner, "QR_ORDERING")
    _, item = create_category_and_item(client, owner["headers"], price=90)
    table = create_table(client, owner["headers"], name="Q2")

    slug = client.get("/api/v1/businesses/me", headers=owner["headers"]).json()["slug"]
    locations = client.get("/api/v1/locations", headers=owner["headers"]).json()
    location = next(l for l in locations if l["id"] == table["id"])
    qr_code = location["qr_url"].split("c=")[1]
    session_token = client.get(
        f"/api/v1/qr/scan/{slug}/{table['id']}", params={"c": qr_code}
    ).json()["session_token"]

    for _ in range(2):
        client.post(
            "/api/v1/qr/orders",
            json={"items": [{"menu_item_id": item["id"], "quantity": 1}]},
            headers={"X-QR-Session": session_token},
        )

    resp = client.get("/api/v1/notifications", headers=owner["headers"])
    assert resp.json()["unread_count"] >= 2

    resp = client.post("/api/v1/notifications/read-all", headers=owner["headers"])
    assert resp.status_code == 204

    resp = client.get("/api/v1/notifications", headers=owner["headers"])
    assert resp.json()["unread_count"] == 0
