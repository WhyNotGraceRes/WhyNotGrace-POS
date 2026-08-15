from tests.helpers import register_and_login


def _create_staff_and_login(client, owner_headers, role: str):
    import uuid

    email = f"staff-{uuid.uuid4().hex[:8]}@example.com"
    mobile = f"9{uuid.uuid4().int % 10**9:09d}"
    resp = client.post(
        "/api/v1/staff",
        json={
            "first_name": "Staffer",
            "last_name": role.title(),
            "email": email,
            "mobile": mobile,
            "password": "StaffPass123",
            "role": role,
        },
        headers=owner_headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.post("/api/v1/auth/login", json={"identifier": email, "password": "StaffPass123"})
    assert resp.status_code == 200, resp.text
    tokens = resp.json()
    return {"headers": {"Authorization": f"Bearer {tokens['access_token']}"}}


def test_kitchen_staff_cannot_create_menu_items(client, db_session):
    owner = register_and_login(client, db_session, business_name="RBAC Biz 1")
    kitchen = _create_staff_and_login(client, owner["headers"], "KITCHEN")

    resp = client.post("/api/v1/categories", json={"name": "Mains"}, headers=owner["headers"])
    category = resp.json()

    resp = client.post(
        "/api/v1/menu/items",
        json={"category_id": category["id"], "name": "Dal Makhani", "base_price": 150},
        headers=kitchen["headers"],
    )
    assert resp.status_code == 403


def test_kitchen_staff_can_view_kitchen_queue(client, db_session):
    owner = register_and_login(client, db_session, business_name="RBAC Biz 2")
    kitchen = _create_staff_and_login(client, owner["headers"], "KITCHEN")

    resp = client.get("/api/v1/kitchen/queue", headers=kitchen["headers"])
    assert resp.status_code == 200


def test_cash_counter_cannot_change_feature_flags(client, db_session):
    owner = register_and_login(client, db_session, business_name="RBAC Biz 3")
    cash_counter = _create_staff_and_login(client, owner["headers"], "CASH_COUNTER")

    resp = client.put("/api/v1/settings/features/DELIVERY", json={"enabled": True}, headers=cash_counter["headers"])
    assert resp.status_code == 403


def test_delivery_staff_cannot_view_reports(client, db_session):
    owner = register_and_login(client, db_session, business_name="RBAC Biz 4")
    delivery = _create_staff_and_login(client, owner["headers"], "DELIVERY")

    resp = client.get("/api/v1/reports/sales", headers=delivery["headers"])
    assert resp.status_code == 403


def test_loyalty_rules_read_requires_operational_role(client, db_session):
    from tests.helpers import enable_feature

    owner = register_and_login(client, db_session, business_name="RBAC Biz 6")
    enable_feature(client, owner["headers"], "LOYALTY")

    resp = client.get("/api/v1/loyalty/rules", headers=owner["headers"])
    assert resp.status_code == 200

    manager = _create_staff_and_login(client, owner["headers"], "MANAGER")
    resp = client.get("/api/v1/loyalty/rules", headers=manager["headers"])
    assert resp.status_code == 200

    for role in ["CASH_COUNTER", "SERVICE_COUNTER", "KITCHEN"]:
        staff = _create_staff_and_login(client, owner["headers"], role)
        resp = client.get("/api/v1/loyalty/rules", headers=staff["headers"])
        assert resp.status_code == 403, f"{role} should not be able to list loyalty rules"


def test_staff_api_rejects_creating_second_owner(client, db_session):
    owner = register_and_login(client, db_session, business_name="RBAC Biz 5")
    resp = client.post(
        "/api/v1/staff",
        json={
            "first_name": "Second",
            "last_name": "Owner",
            "email": "second-owner@example.com",
            "mobile": "9123456780",
            "password": "SomePass123",
            "role": "OWNER",
        },
        headers=owner["headers"],
    )
    assert resp.status_code == 400
