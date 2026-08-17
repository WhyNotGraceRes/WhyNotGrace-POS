from tests.helpers import create_category_and_item, create_table, enable_feature, register_and_login


def test_ws_rejects_connection_with_no_token(client):
    try:
        with client.websocket_connect("/api/v1/ws"):
            raised = False
    except Exception:
        raised = True
    assert raised


def test_ws_rejects_connection_with_invalid_token(client):
    try:
        with client.websocket_connect("/api/v1/ws?token=not-a-real-token"):
            raised = False
    except Exception:
        raised = True
    assert raised


def test_ws_delivers_invalidate_message_on_new_order(client, db_session):
    owner = register_and_login(client, db_session, business_name="WS Biz 1")
    _, item = create_category_and_item(client, owner["headers"], price=100)
    table = create_table(client, owner["headers"])
    token = owner["tokens"]["access_token"]

    with client.websocket_connect(f"/api/v1/ws?token={token}") as websocket:
        client.post(
            "/api/v1/orders",
            json={
                "location_id": table["id"], "source": "DINE_IN", "pricing_context": "DINE_IN",
                "items": [{"menu_item_id": item["id"], "quantity": 1}],
            },
            headers=owner["headers"],
        )
        message = websocket.receive_json()
        assert message["type"] == "invalidate"
        assert "orders" in message["keys"]


def test_ws_delivers_notification_message_on_qr_order(client, db_session):
    owner = register_and_login(client, db_session, business_name="WS Biz 2")
    enable_feature(client, db_session, owner, "QR_ORDERING")
    _, item = create_category_and_item(client, owner["headers"], price=90)
    table = create_table(client, owner["headers"], name="Q1")
    token = owner["tokens"]["access_token"]

    slug = client.get("/api/v1/businesses/me", headers=owner["headers"]).json()["slug"]
    locations = client.get("/api/v1/locations", headers=owner["headers"]).json()
    location = next(l for l in locations if l["id"] == table["id"])
    qr_code = location["qr_url"].split("c=")[1]
    session_token = client.get(
        f"/api/v1/qr/scan/{slug}/{table['id']}", params={"c": qr_code}
    ).json()["session_token"]

    with client.websocket_connect(f"/api/v1/ws?token={token}") as websocket:
        client.post(
            "/api/v1/qr/orders",
            json={"items": [{"menu_item_id": item["id"], "quantity": 1}]},
            headers={"X-QR-Session": session_token},
        )
        seen_types = set()
        for _ in range(4):
            message = websocket.receive_json()
            for key in message["keys"]:
                seen_types.add(key)
            if "notifications" in seen_types:
                break
        assert "notifications" in seen_types
