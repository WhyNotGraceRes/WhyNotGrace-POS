"""Business provisioning and entitlement control by platform staff — see
app.services.platform_service and app.api.platform.{businesses,features,toggles}.
"""
import uuid

from tests.helpers import platform_login, register_and_login


def _provision_payload(**overrides):
    payload = {
        "business_name": f"Provisioned Biz {uuid.uuid4().hex[:6]}",
        "business_type": "CAFE",
        "owner_first_name": "Grace",
        "owner_last_name": "Hopper",
        "owner_email": f"grace-{uuid.uuid4().hex[:8]}@example.com",
        "owner_mobile": f"9{uuid.uuid4().int % 10**9:09d}",
        "owner_password": "CorrectHorse123",
    }
    payload.update(overrides)
    return payload


def test_provisioning_creates_a_working_owner_login(client, db_session):
    platform_headers = platform_login(client, db_session)
    payload = _provision_payload()

    resp = client.post("/api/v1/platform/businesses", json=payload, headers=platform_headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["owner_email"] == payload["owner_email"].lower()

    # Created active and pre-verified — no verify-email step exists any more.
    resp = client.post(
        "/api/v1/auth/login", json={"identifier": payload["owner_email"], "password": payload["owner_password"]}
    )
    assert resp.status_code == 200, resp.text


def test_provisioning_duplicate_email_rejected(client, db_session):
    platform_headers = platform_login(client, db_session)
    payload = _provision_payload()

    resp = client.post("/api/v1/platform/businesses", json=payload, headers=platform_headers)
    assert resp.status_code == 201

    resp = client.post(
        "/api/v1/platform/businesses",
        json=_provision_payload(owner_email=payload["owner_email"], owner_mobile=payload["owner_mobile"]),
        headers=platform_headers,
    )
    assert resp.status_code == 409


def test_a_new_business_starts_with_only_core_pos_enabled(client, db_session):
    platform_headers = platform_login(client, db_session)
    resp = client.post("/api/v1/platform/businesses", json=_provision_payload(), headers=platform_headers)
    business_id = resp.json()["business_id"]

    resp = client.get(f"/api/v1/platform/businesses/{business_id}/features", headers=platform_headers)
    assert resp.status_code == 200, resp.text
    flags = {f["module"]: f["enabled"] for f in resp.json()}
    assert flags["CORE_POS"] is True
    assert flags["QR_ORDERING"] is False
    assert flags["ONLINE_WEBSITE"] is False
    assert flags["DELIVERY"] is False


def test_platform_can_enable_a_module_that_then_works_for_the_owner(client, db_session):
    owner = register_and_login(client, db_session, business_name="Entitlement Biz 1")
    platform_headers = platform_login(client, db_session)

    # Blocked before the module is on.
    resp = client.get("/api/v1/delivery/orders", headers=owner["headers"])
    assert resp.status_code == 403

    resp = client.put(
        f"/api/v1/platform/businesses/{owner['business_id']}/features/DELIVERY",
        json={"enabled": True}, headers=platform_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["enabled"] is True

    resp = client.get("/api/v1/delivery/orders", headers=owner["headers"])
    assert resp.status_code == 200


def test_owner_cannot_write_a_feature_flag_any_more(client, db_session):
    """The hole this whole layer exists to close: an owner must not be able
    to self-enable a paid module for free."""
    owner = register_and_login(client, db_session, business_name="Entitlement Biz 2")

    resp = client.put("/api/v1/settings/features/DELIVERY", json={"enabled": True}, headers=owner["headers"])
    assert resp.status_code == 404  # the write route doesn't exist on the business side at all

    resp = client.get("/api/v1/settings/features", headers=owner["headers"])
    assert resp.status_code == 200
    flags = {f["module"]: f["enabled"] for f in resp.json()}
    assert flags["DELIVERY"] is False


def test_core_pos_cannot_be_disabled_even_by_the_platform(client, db_session):
    owner = register_and_login(client, db_session, business_name="Entitlement Biz 3")
    platform_headers = platform_login(client, db_session)

    resp = client.put(
        f"/api/v1/platform/businesses/{owner['business_id']}/features/CORE_POS",
        json={"enabled": False}, headers=platform_headers,
    )
    assert resp.status_code == 400


def test_platform_can_set_an_entitlement_toggle_an_owner_cannot(client, db_session, monkeypatch):
    """An owner_editable=False toggle is refused for an owner and accepted
    from the platform — see toggle_service.set_toggle vs.
    platform_set_toggle. No real toggle in the registry is entitlement-class
    yet (every one shipped so far is a preference), so this registers a
    throwaway one, the same way test_invoice_integrity.py's
    test_entitlement_toggles_are_refused_for_owners does."""
    from app.core.toggles import ToggleDef, ToggleGroup, _REGISTRY

    entitlement = ToggleDef(
        key="billing.platform_test_entitlement", group=ToggleGroup.BILLING, default=True,
        owner_editable=False, label="Plan-controlled thing", description="test",
    )
    monkeypatch.setitem(_REGISTRY, entitlement.key, entitlement)
    key = entitlement.key

    owner = register_and_login(client, db_session, business_name="Entitlement Biz 4")
    platform_headers = platform_login(client, db_session)

    resp = client.put(f"/api/v1/settings/toggles/{key}", json={"enabled": False}, headers=owner["headers"])
    assert resp.status_code == 403

    resp = client.put(
        f"/api/v1/platform/businesses/{owner['business_id']}/toggles/{key}",
        json={"enabled": False}, headers=platform_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["enabled"] is False

    # The owner-facing read reflects the platform's change.
    resp = client.get("/api/v1/settings/toggles", headers=owner["headers"])
    row = next(t for t in resp.json() if t["key"] == key)
    assert row["enabled"] is False
    assert row["is_overridden"] is True


def test_business_active_kill_switch_blocks_dashboard_login(client, db_session):
    owner = register_and_login(client, db_session, business_name="Kill Switch Biz")
    platform_headers = platform_login(client, db_session)

    resp = client.get("/api/v1/orders", headers=owner["headers"])
    assert resp.status_code == 200

    resp = client.put(
        f"/api/v1/platform/businesses/{owner['business_id']}/active",
        json={"is_active": False}, headers=platform_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_active"] is False

    resp = client.get("/api/v1/orders", headers=owner["headers"])
    assert resp.status_code == 403

    # Reversible.
    resp = client.put(
        f"/api/v1/platform/businesses/{owner['business_id']}/active",
        json={"is_active": True}, headers=platform_headers,
    )
    assert resp.status_code == 200

    resp = client.get("/api/v1/orders", headers=owner["headers"])
    assert resp.status_code == 200


def test_platform_businesses_endpoints_reject_a_business_token(client, db_session):
    owner = register_and_login(client, db_session, business_name="No Access Biz")

    resp = client.get("/api/v1/platform/businesses", headers=owner["headers"])
    assert resp.status_code == 401

    resp = client.post("/api/v1/platform/businesses", json=_provision_payload(), headers=owner["headers"])
    assert resp.status_code == 401
