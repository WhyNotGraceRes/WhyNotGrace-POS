import uuid

from app.core.security import hash_password
from app.models.enums import PlatformRole
from app.models.platform_user import PlatformUser


def platform_login(client, db_session):
    """Creates a throwaway platform admin directly via the ORM — there is no
    self-registration for platform accounts, only provisioning by an
    existing one (see app.services.platform_service) — and logs in.
    """
    email = f"platform-{uuid.uuid4().hex[:8]}@example.com"
    password = "PlatformPass123"
    pu = PlatformUser(
        email=email, password_hash=hash_password(password),
        first_name="Platform", last_name="Admin", role=PlatformRole.SUPERADMIN, is_active=True,
    )
    db_session.add(pu)
    db_session.flush()

    resp = client.post("/api/v1/platform/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def register_and_login(client, db_session, *, business_name: str | None = None, role_password="SuperSecret123"):
    """Provisions a business via the platform surface and logs in as its
    owner. There is no self-registration any more (see app.api.auth) — a
    business only exists because a platform admin created it, and the owner
    account it creates is active and pre-verified from the start, the same
    "provisioned, not self-served" precedent app/api/staff.py already sets
    for staff created by an owner.
    """
    payload = {
        "business_name": business_name or f"Test Biz {uuid.uuid4().hex[:6]}",
        "business_type": "RESTAURANT",
        "owner_first_name": "Ada",
        "owner_last_name": "Owner",
        "email": f"owner-{uuid.uuid4().hex[:8]}@example.com",
        "mobile": f"9{uuid.uuid4().int % 10**9:09d}",
        "password": role_password,
    }

    platform_headers = platform_login(client, db_session)
    resp = client.post(
        "/api/v1/platform/businesses",
        json={
            "business_name": payload["business_name"], "business_type": payload["business_type"],
            "owner_first_name": payload["owner_first_name"], "owner_last_name": payload["owner_last_name"],
            "owner_email": payload["email"], "owner_mobile": payload["mobile"],
            "owner_password": payload["password"],
        },
        headers=platform_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()

    resp = client.post("/api/v1/auth/login", json={"identifier": payload["email"], "password": role_password})
    assert resp.status_code == 200, resp.text
    tokens = resp.json()

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    return {
        "payload": payload,
        "business_id": data["business_id"],
        "user_id": data["owner_user_id"],
        "tokens": tokens,
        "headers": headers,
    }


def _set_feature(client, db_session, ctx, module: str, enabled: bool):
    """ctx is the dict register_and_login returns — needs its business_id,
    not its (owner) headers, since only the platform can write a
    FeatureFlag now (see app.api.feature_flags's read-only-for-owners
    docstring)."""
    platform_headers = platform_login(client, db_session)
    return client.put(
        f"/api/v1/platform/businesses/{ctx['business_id']}/features/{module}",
        json={"enabled": enabled}, headers=platform_headers,
    )


def enable_feature(client, db_session, ctx, module: str):
    resp = _set_feature(client, db_session, ctx, module, True)
    assert resp.status_code == 200, resp.text
    return resp.json()


def disable_feature(client, db_session, ctx, module: str):
    return _set_feature(client, db_session, ctx, module, False)


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
