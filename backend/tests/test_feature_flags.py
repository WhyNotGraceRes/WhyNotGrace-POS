from tests.helpers import enable_feature, register_and_login


def test_delivery_disabled_by_default_and_blocks_endpoint(client, db_session):
    owner = register_and_login(client, db_session, business_name="Feature Flag Biz 1")

    resp = client.get("/api/v1/settings/features", headers=owner["headers"])
    flags = {f["module"]: f["enabled"] for f in resp.json()}
    assert flags["DELIVERY"] is False
    assert flags["CORE_POS"] is True  # always-on

    resp = client.get("/api/v1/delivery/orders", headers=owner["headers"])
    assert resp.status_code == 403


def test_core_pos_cannot_be_disabled(client, db_session):
    owner = register_and_login(client, db_session, business_name="Feature Flag Biz 2")
    resp = client.put("/api/v1/settings/features/CORE_POS", json={"enabled": False}, headers=owner["headers"])
    assert resp.status_code == 400


def test_enabling_delivery_unlocks_the_endpoint(client, db_session):
    owner = register_and_login(client, db_session, business_name="Feature Flag Biz 3")
    enable_feature(client, owner["headers"], "DELIVERY")

    resp = client.get("/api/v1/delivery/orders", headers=owner["headers"])
    assert resp.status_code == 200


def test_hotel_rooms_disabled_blocks_room_creation(client, db_session):
    owner = register_and_login(client, db_session, business_name="Feature Flag Biz 4")
    resp = client.post(
        "/api/v1/rooms", json={"location_type": "ROOM", "name": "101"}, headers=owner["headers"]
    )
    assert resp.status_code == 403

    enable_feature(client, owner["headers"], "HOTEL_ROOMS")
    resp = client.post(
        "/api/v1/rooms", json={"location_type": "ROOM", "name": "101"}, headers=owner["headers"]
    )
    assert resp.status_code == 201
