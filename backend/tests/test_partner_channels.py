"""Security properties of the partner sales channel.

The channel exists so a business's own website can submit orders into
WhyNotGrace. That means handing an outside process a credential that
creates real orders, so what matters is not that the happy path works but
that everything around it fails closed:

  * a credential reaches exactly one business, and nothing else
  * a compromised sender cannot choose its own prices
  * a captured request cannot be replayed
  * a retried request cannot double-charge the kitchen
  * revocation is immediate
  * nothing works until an owner has deliberately turned it on

Each test below is one of those claims.
"""
import json
import time
import uuid

import pytest

from app.core.partner_auth import build_signing_string, sign
from tests.helpers import create_category_and_item, enable_feature, register_and_login

CHANNEL_PATH = "/api/v1/channels/orders"


def _signed_headers(key_id: str, secret: str, body: bytes, *, path: str = CHANNEL_PATH,
                    method: str = "POST", timestamp: str | None = None, nonce: str | None = None):
    ts = timestamp or str(int(time.time()))
    nc = nonce or uuid.uuid4().hex
    signing_string = build_signing_string(method=method, path=path, timestamp=ts, nonce=nc, body=body)
    return {
        "X-Partner-Key": key_id,
        "X-Partner-Timestamp": ts,
        "X-Partner-Nonce": nc,
        "X-Partner-Signature": sign(secret, signing_string),
        "Content-Type": "application/json",
    }


def _post(client, key_id, secret, payload: dict, **kw):
    body = json.dumps(payload).encode()
    headers = _signed_headers(key_id, secret, body, **kw)
    return client.post(CHANNEL_PATH, content=body, headers=headers)


@pytest.fixture()
def channel(client, db_session):
    """A fully provisioned channel: owner, enabled module, menu item, key,
    and a mapping for the partner's own item reference."""
    owner = register_and_login(client, db_session, business_name=f"Partner Biz {uuid.uuid4().hex[:6]}")
    enable_feature(client, owner["headers"], "PARTNER_CHANNEL")
    _category, item = create_category_and_item(client, owner["headers"], price=250.0)

    resp = client.post("/api/v1/partner-channels", json={"name": "Sweet Home site"}, headers=owner["headers"])
    assert resp.status_code == 201, resp.text
    created = resp.json()

    resp = client.put(
        f"/api/v1/partner-channels/{created['id']}/menu-map",
        json={"external_ref": "sweet-home-paneer", "menu_item_id": item["id"]},
        headers=owner["headers"],
    )
    assert resp.status_code == 200, resp.text

    return {
        "owner": owner,
        "id": created["id"],
        "key_id": created["key_id"],
        "secret": created["secret"],
        "item": item,
    }


ORDER = {"items": [{"external_ref": "sweet-home-paneer", "quantity": 2}], "fulfilment": "PICKUP"}


# ---------------------------------------------------------------------------
# it works at all
# ---------------------------------------------------------------------------

def test_provisioned_channel_can_submit_an_order(client, channel):
    resp = _post(client, channel["key_id"], channel["secret"], ORDER)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["order_number"]
    # 2 x 250, priced by the server from the mapping — not from the request.
    assert body["subtotal"] == 500.0
    assert body["duplicate"] is False


def test_secret_is_returned_once_and_never_again(client, channel):
    """A secret that can be re-read is one that leaks through every screen
    and log that touches it afterwards."""
    resp = client.get("/api/v1/partner-channels", headers=channel["owner"]["headers"])
    assert resp.status_code == 200
    listed = [c for c in resp.json() if c["id"] == channel["id"]][0]
    assert "secret" not in listed
    assert channel["secret"] not in json.dumps(resp.json())


# ---------------------------------------------------------------------------
# price integrity
# ---------------------------------------------------------------------------

def test_price_in_the_payload_is_ignored(client, channel):
    """The schema has no price field, so a sender that adds one must not be
    able to influence the total. This is the whole reason the channel takes
    item references instead of a cart."""
    payload = {
        "items": [{"external_ref": "sweet-home-paneer", "quantity": 2, "price": 1, "unit_price": 1}],
        "fulfilment": "PICKUP",
        "subtotal": 2,
        "total": 2,
    }
    resp = _post(client, channel["key_id"], channel["secret"], payload)
    assert resp.status_code == 201, resp.text
    assert resp.json()["subtotal"] == 500.0


def test_unmapped_item_is_rejected_not_guessed(client, channel):
    """Guessing — by name match or a default — would silently charge a guest
    for a different dish. A rejected order is the better failure."""
    payload = {"items": [{"external_ref": "not-mapped-at-all", "quantity": 1}], "fulfilment": "PICKUP"}
    resp = _post(client, channel["key_id"], channel["secret"], payload)
    assert resp.status_code == 400
    assert "not-mapped-at-all" in resp.text


# ---------------------------------------------------------------------------
# tenant isolation
# ---------------------------------------------------------------------------

def test_channel_cannot_reach_another_business(client, db_session, channel):
    """Business B provisions its own channel and maps its own item. B's
    credential must not be able to order A's item, even by ref name."""
    other = register_and_login(client, db_session, business_name=f"Other Biz {uuid.uuid4().hex[:6]}")
    enable_feature(client, other["headers"], "PARTNER_CHANNEL")
    create_category_and_item(client, other["headers"], price=999.0)

    resp = client.post("/api/v1/partner-channels", json={"name": "Other site"}, headers=other["headers"])
    other_channel = resp.json()

    # A's ref is unknown to B's channel — mappings are per channel.
    resp = _post(client, other_channel["key_id"], other_channel["secret"], ORDER)
    assert resp.status_code == 400


def test_owner_cannot_map_another_businesss_menu_item(client, db_session, channel):
    other = register_and_login(client, db_session, business_name=f"Third Biz {uuid.uuid4().hex[:6]}")
    _other_category, other_item = create_category_and_item(client, other["headers"], price=100.0)

    resp = client.put(
        f"/api/v1/partner-channels/{channel['id']}/menu-map",
        json={"external_ref": "sneaky", "menu_item_id": other_item["id"]},
        headers=channel["owner"]["headers"],
    )
    assert resp.status_code == 400


def test_partner_credential_does_not_unlock_staff_endpoints(client, channel):
    """A channel key is an order-submission capability, not an API account."""
    body = b"{}"
    headers = _signed_headers(channel["key_id"], channel["secret"], body, path="/api/v1/orders", method="GET")
    for path in ["/api/v1/orders", "/api/v1/customers", "/api/v1/reports/sales", "/api/v1/staff"]:
        resp = client.get(path, headers=headers)
        assert resp.status_code in (401, 403), f"{path} returned {resp.status_code}"


# ---------------------------------------------------------------------------
# signature, replay, freshness
# ---------------------------------------------------------------------------

def test_unsigned_request_is_rejected(client, channel):
    resp = client.post(CHANNEL_PATH, json=ORDER)
    assert resp.status_code == 401


def test_wrong_secret_is_rejected(client, channel):
    resp = _post(client, channel["key_id"], "not-the-real-secret", ORDER)
    assert resp.status_code == 401


def test_unknown_key_is_rejected(client, channel):
    resp = _post(client, "wng_does_not_exist", channel["secret"], ORDER)
    assert resp.status_code == 401


def test_tampering_with_the_body_invalidates_the_signature(client, channel):
    """The signature covers a hash of the exact bytes, so changing the
    quantity after signing must not verify."""
    body = json.dumps(ORDER).encode()
    headers = _signed_headers(channel["key_id"], channel["secret"], body)
    tampered = json.dumps({"items": [{"external_ref": "sweet-home-paneer", "quantity": 50}],
                           "fulfilment": "PICKUP"}).encode()
    resp = client.post(CHANNEL_PATH, content=tampered, headers=headers)
    assert resp.status_code == 401


def test_replaying_a_valid_request_is_rejected(client, channel):
    """The captured request is byte-identical and its signature is genuine —
    only the spent nonce stops it."""
    body = json.dumps(ORDER).encode()
    headers = _signed_headers(channel["key_id"], channel["secret"], body)

    first = client.post(CHANNEL_PATH, content=body, headers=headers)
    assert first.status_code == 201, first.text

    replay = client.post(CHANNEL_PATH, content=body, headers=headers)
    assert replay.status_code == 401


def test_stale_timestamp_is_rejected(client, channel):
    old = str(int(time.time()) - 4000)
    resp = _post(client, channel["key_id"], channel["secret"], ORDER, timestamp=old)
    assert resp.status_code == 401


def test_far_future_timestamp_is_rejected(client, channel):
    """A future timestamp would otherwise stay replayable indefinitely."""
    future = str(int(time.time()) + 4000)
    resp = _post(client, channel["key_id"], channel["secret"], ORDER, timestamp=future)
    assert resp.status_code == 401


def test_signature_from_another_path_is_not_reusable(client, channel):
    """The path is part of the signed string precisely so a signature cannot
    be lifted from one endpoint to another."""
    body = json.dumps(ORDER).encode()
    headers = _signed_headers(channel["key_id"], channel["secret"], body, path="/api/v1/somewhere-else")
    resp = client.post(CHANNEL_PATH, content=body, headers=headers)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# idempotency
# ---------------------------------------------------------------------------

def test_retry_with_the_same_idempotency_key_returns_the_same_order(client, channel):
    """A partner that times out and retries must not produce a second
    ticket in the kitchen. Each attempt is separately signed with a fresh
    nonce — this is a genuine retry, not a replay."""
    payload = dict(ORDER, idempotency_key="sweet-home-order-4711")

    first = _post(client, channel["key_id"], channel["secret"], payload)
    assert first.status_code == 201, first.text

    second = _post(client, channel["key_id"], channel["secret"], payload)
    assert second.status_code == 201, second.text

    assert second.json()["order_id"] == first.json()["order_id"]
    assert second.json()["duplicate"] is True


def test_different_idempotency_keys_create_different_orders(client, channel):
    a = _post(client, channel["key_id"], channel["secret"], dict(ORDER, idempotency_key="k-a"))
    b = _post(client, channel["key_id"], channel["secret"], dict(ORDER, idempotency_key="k-b"))
    assert a.json()["order_id"] != b.json()["order_id"]


# ---------------------------------------------------------------------------
# the two gates: provisioning and the feature flag
# ---------------------------------------------------------------------------

def test_revocation_takes_effect_immediately(client, channel):
    assert _post(client, channel["key_id"], channel["secret"], ORDER).status_code == 201

    resp = client.delete(f"/api/v1/partner-channels/{channel['id']}", headers=channel["owner"]["headers"])
    assert resp.status_code == 200

    assert _post(client, channel["key_id"], channel["secret"], ORDER).status_code == 401


def test_rotating_the_secret_invalidates_the_old_one(client, channel):
    resp = client.post(f"/api/v1/partner-channels/{channel['id']}/rotate", headers=channel["owner"]["headers"])
    assert resp.status_code == 200
    new_secret = resp.json()["secret"]
    assert new_secret != channel["secret"]

    assert _post(client, channel["key_id"], channel["secret"], ORDER).status_code == 401
    assert _post(client, channel["key_id"], new_secret, ORDER).status_code == 201


def test_disabling_the_module_stops_an_already_issued_key(client, channel):
    """Two independent gates: the credential exists, but the business has
    switched inbound submission off."""
    resp = client.put(
        "/api/v1/settings/features/PARTNER_CHANNEL",
        json={"enabled": False},
        headers=channel["owner"]["headers"],
    )
    assert resp.status_code == 200

    resp = _post(client, channel["key_id"], channel["secret"], ORDER)
    assert resp.status_code == 403


def test_non_owner_staff_cannot_provision_a_channel(client, db_session, channel):
    """Issuing a credential that can create orders is closer to adding a
    staff member than to editing a menu, so it is owner-only."""
    resp = client.post(
        "/api/v1/staff",
        json={
            "first_name": "Mgr", "last_name": "One",
            "email": f"mgr-{uuid.uuid4().hex[:8]}@example.com",
            "mobile": f"9{uuid.uuid4().int % 10**9:09d}",
            "role": "MANAGER", "password": "ManagerPass123",
        },
        headers=channel["owner"]["headers"],
    )
    assert resp.status_code == 201, resp.text
    staff_email = resp.json()["email"]

    login = client.post("/api/v1/auth/login", json={"identifier": staff_email, "password": "ManagerPass123"})
    assert login.status_code == 200, login.text
    mgr_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = client.post("/api/v1/partner-channels", json={"name": "Sneaky"}, headers=mgr_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# kitchen safety
# ---------------------------------------------------------------------------

def test_partner_order_does_not_reach_the_kitchen_before_payment(client, channel):
    """Submitted with hold_kot, exactly like a normal pickup/delivery order.
    A partner site claiming an order is paid is not evidence of payment."""
    resp = _post(client, channel["key_id"], channel["secret"], ORDER)
    assert resp.status_code == 201

    queue = client.get("/api/v1/kitchen/queue", headers=channel["owner"]["headers"])
    assert queue.status_code == 200
    order_id = resp.json()["order_id"]
    assert all(kot["order_id"] != order_id for kot in queue.json())
