import hashlib
import hmac
import json
import uuid

from tests.helpers import register_and_login


def test_razorpay_order_requires_online_payment_feature(client, db_session):
    owner = register_and_login(client, db_session, business_name="Integration Biz 1")
    resp = client.post(
        "/api/v1/payments/razorpay/order", json={"bill_id": "00000000-0000-0000-0000-000000000000"},
        headers=owner["headers"],
    )
    assert resp.status_code == 403  # feature flag not enabled


def test_razorpay_webhook_rejects_invalid_signature(client):
    resp = client.post(
        "/api/v1/payments/webhooks/razorpay",
        headers={"X-Razorpay-Signature": "not-a-real-signature"},
        content=b'{"event": "payment.captured"}',
    )
    # Without RAZORPAY_WEBHOOK_SECRET configured, the endpoint must fail
    # closed (503) rather than silently accept an unverifiable payload.
    assert resp.status_code == 503


def test_zomato_menu_sync_reports_not_configured_rather_than_faking_success(client, db_session):
    owner = register_and_login(client, db_session, business_name="Integration Biz 2")
    from tests.helpers import enable_feature

    enable_feature(client, db_session, owner, "ZOMATO")
    resp = client.post("/api/v1/integrations/ZOMATO/menu-sync", headers=owner["headers"])
    assert resp.status_code == 503
    assert "not configured" in resp.json()["detail"].lower()


def test_integration_credentials_never_echoed_back(client, db_session):
    owner = register_and_login(client, db_session, business_name="Integration Biz 3")
    resp = client.put(
        "/api/v1/integrations/ZOMATO/credentials",
        json={"credentials": {"client_id": "abc", "client_secret": "super-secret"}},
        headers=owner["headers"],
    )
    assert resp.status_code == 200
    assert "super-secret" not in resp.text
    assert "client_secret" not in resp.text


def _connect_razorpay(client, headers, *, key_id, key_secret, webhook_secret):
    resp = client.put(
        "/api/v1/integrations/RAZORPAY/credentials",
        json={"credentials": {"key_id": key_id, "key_secret": key_secret, "webhook_secret": webhook_secret}},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_razorpay_business_credentials_never_leak_secret_and_are_tenant_isolated(client, db_session):
    owner_a = register_and_login(client, db_session, business_name="Razorpay Biz A")
    owner_b = register_and_login(client, db_session, business_name="Razorpay Biz B")

    resp_a = _connect_razorpay(
        client, owner_a["headers"], key_id="rzp_test_AAAA1111", key_secret="secret-A-only", webhook_secret="whsecA"
    )
    assert "secret-A-only" not in json.dumps(resp_a)
    assert "whsecA" not in json.dumps(resp_a)
    assert resp_a["masked_key_id"] is not None
    assert "secret-A-only" not in resp_a["masked_key_id"]

    resp_b = _connect_razorpay(
        client, owner_b["headers"], key_id="rzp_test_BBBB2222", key_secret="secret-B-only", webhook_secret="whsecB"
    )
    assert resp_a["masked_key_id"] != resp_b["masked_key_id"]

    # Listing integrations must never expose either business's secret, and
    # each business must only ever see its own masked key.
    list_a = client.get("/api/v1/integrations", headers=owner_a["headers"])
    assert list_a.status_code == 200
    assert "secret-A-only" not in list_a.text and "secret-B-only" not in list_a.text
    razorpay_row_a = next(i for i in list_a.json() if i["provider"] == "RAZORPAY")
    assert razorpay_row_a["masked_key_id"] == resp_a["masked_key_id"]

    list_b = client.get("/api/v1/integrations", headers=owner_b["headers"])
    razorpay_row_b = next(i for i in list_b.json() if i["provider"] == "RAZORPAY")
    assert razorpay_row_b["masked_key_id"] == resp_b["masked_key_id"]
    assert razorpay_row_b["masked_key_id"] != razorpay_row_a["masked_key_id"]


def test_razorpay_credential_resolution_never_mixes_businesses(client, db_session):
    """Unit-level check of the actual resolver used before every Razorpay
    API call: Business A's request must resolve Business A's credentials,
    never Business B's, and a business with nothing connected must fall
    back to the (empty, in tests) global config rather than someone else's.
    """
    from app.models.enums import IntegrationProvider
    from app.services import payment_service

    owner_a = register_and_login(client, db_session, business_name="Razorpay Biz C")
    owner_b = register_and_login(client, db_session, business_name="Razorpay Biz D")
    _connect_razorpay(client, owner_a["headers"], key_id="rzp_c_key", key_secret="rzp_c_secret", webhook_secret="rzp_c_wh")

    creds_a = payment_service._resolve_razorpay_credentials(db_session, uuid.UUID(owner_a["business_id"]))
    assert creds_a["key_id"] == "rzp_c_key"
    assert creds_a["key_secret"] == "rzp_c_secret"

    creds_b = payment_service._resolve_razorpay_credentials(db_session, uuid.UUID(owner_b["business_id"]))
    assert creds_b["key_id"] != "rzp_c_key"  # global fallback (empty in tests), never A's key

    from app.services import integration_service

    b_direct = integration_service.get_business_credentials(db_session, uuid.UUID(owner_b["business_id"]), IntegrationProvider.RAZORPAY)
    assert b_direct == {}  # B never connected anything of its own


def test_razorpay_webhook_missing_credentials_fails_closed_per_business(client, db_session):
    owner = register_and_login(client, db_session, business_name="Razorpay Biz E")
    resp = client.post(
        f"/api/v1/payments/webhooks/razorpay/{owner['business_id']}",
        headers={"X-Razorpay-Signature": "irrelevant-since-not-configured"},
        content=b'{"event": "payment.captured"}',
    )
    assert resp.status_code == 503


def test_razorpay_webhook_per_business_verifies_against_that_businesss_own_secret(client, db_session):
    owner_a = register_and_login(client, db_session, business_name="Razorpay Biz F")
    owner_b = register_and_login(client, db_session, business_name="Razorpay Biz G")
    _connect_razorpay(client, owner_a["headers"], key_id="rzp_f_key", key_secret="rzp_f_secret", webhook_secret="whsec-f-only")

    raw_body = json.dumps({"id": f"evt_{uuid.uuid4().hex[:12]}", "event": "payment.captured", "payload": {}}).encode()
    valid_signature = hmac.new(b"whsec-f-only", raw_body, hashlib.sha256).hexdigest()

    # Correct business + correct signature -> accepted.
    resp = client.post(
        f"/api/v1/payments/webhooks/razorpay/{owner_a['business_id']}",
        headers={"X-Razorpay-Signature": valid_signature}, content=raw_body,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "PROCESSED"

    # Business B has no Razorpay connected and global fallback is empty in
    # tests, so even a well-formed signature for A's secret must fail
    # closed with 503 (not configured) rather than accept a foreign event.
    raw_body_2 = json.dumps({"id": f"evt_{uuid.uuid4().hex[:12]}", "event": "payment.captured", "payload": {}}).encode()
    signature_for_a_secret = hmac.new(b"whsec-f-only", raw_body_2, hashlib.sha256).hexdigest()
    resp = client.post(
        f"/api/v1/payments/webhooks/razorpay/{owner_b['business_id']}",
        headers={"X-Razorpay-Signature": signature_for_a_secret}, content=raw_body_2,
    )
    assert resp.status_code == 503

    # Wrong signature against A's own URL must be rejected.
    raw_body_3 = json.dumps({"id": f"evt_{uuid.uuid4().hex[:12]}", "event": "payment.captured", "payload": {}}).encode()
    resp = client.post(
        f"/api/v1/payments/webhooks/razorpay/{owner_a['business_id']}",
        headers={"X-Razorpay-Signature": "totally-wrong"}, content=raw_body_3,
    )
    assert resp.status_code == 400
