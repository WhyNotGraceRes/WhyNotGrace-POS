import uuid

from app.services import auth_service
from app.models.user import User


def register_and_login(client, db_session, *, business_name: str | None = None, role_password="SuperSecret123"):
    payload = {
        "business_name": business_name or f"Test Biz {uuid.uuid4().hex[:6]}",
        "business_type": "RESTAURANT",
        "owner_first_name": "Ada",
        "owner_last_name": "Owner",
        "email": f"owner-{uuid.uuid4().hex[:8]}@example.com",
        "mobile": f"9{uuid.uuid4().int % 10**9:09d}",
        "password": role_password,
        "confirm_password": role_password,
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()

    user = db_session.query(User).filter(User.email == payload["email"].lower()).first()
    code = auth_service._issue_verification_code(db_session, user)
    db_session.flush()

    resp = client.post("/api/v1/auth/verify-email", json={"email": payload["email"], "code": code})
    assert resp.status_code == 200, resp.text

    resp = client.post("/api/v1/auth/login", json={"identifier": payload["email"], "password": role_password})
    assert resp.status_code == 200, resp.text
    tokens = resp.json()

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    return {
        "payload": payload,
        "business_id": data["business_id"],
        "user_id": data["user_id"],
        "tokens": tokens,
        "headers": headers,
    }


def enable_feature(client, headers, module: str):
    resp = client.put(f"/api/v1/settings/features/{module}", json={"enabled": True}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def create_category_and_item(client, headers, *, price: float = 200.0):
    resp = client.post("/api/v1/categories", json={"name": "Starters"}, headers=headers)
    assert resp.status_code == 201, resp.text
    category = resp.json()

    resp = client.post(
        "/api/v1/menu/items",
        json={
            "category_id": category["id"],
            "name": "Paneer Tikka",
            "base_price": price,
            "is_veg": True,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return category, resp.json()


def create_table(client, headers, *, name="T1"):
    resp = client.post("/api/v1/tables", json={"location_type": "TABLE", "name": name, "capacity": 4}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()
