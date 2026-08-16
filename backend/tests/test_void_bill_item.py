"""Voiding one line on a bill.

Voiding a whole bill already worked; striking a single line did not, which
left a cashier with no honest way to handle the most ordinary thing that
happens at a counter — a dish sent back, or rung up twice. The interesting
properties are that the line stops counting toward every derived total, that
it does not come back when the bill is refreshed from the order session, and
that it does not print on the guest's copy while staying on the record.
"""
import uuid

import pytest

from app.core import toggles
from tests.helpers import create_category_and_item, create_table, register_and_login


def _create_staff_and_login(client, owner_headers, role: str):
    email = f"staff-{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post(
        "/api/v1/staff",
        json={
            "first_name": "Staffer", "last_name": role.title(), "email": email,
            "mobile": f"9{uuid.uuid4().int % 10**9:09d}", "password": "StaffPass123", "role": role,
        },
        headers=owner_headers,
    )
    assert resp.status_code == 201, resp.text
    resp = client.post("/api/v1/auth/login", json={"identifier": email, "password": "StaffPass123"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _order(client, headers, table_id, item_id, qty=1):
    resp = client.post(
        "/api/v1/orders",
        json={
            "location_id": table_id, "source": "DINE_IN", "pricing_context": "DINE_IN",
            "items": [{"menu_item_id": item_id, "variant_id": None, "quantity": qty, "option_ids": []}],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _bill(client, headers, session_id):
    resp = client.post("/api/v1/billing/generate", json={"session_id": session_id}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture()
def shop(client, db_session):
    owner = register_and_login(client, db_session, business_name=f"Void Item Biz {uuid.uuid4().hex[:6]}")
    _category, item = create_category_and_item(client, owner["headers"], price=100.0)
    client.put(
        "/api/v1/settings",
        json={"default_tax_percent": 0, "default_service_charge_percent": 0},
        headers=owner["headers"],
    )
    # Off by default here so each test switches on only the rule it is about.
    for key in (toggles.VOID_REQUIRES_REASON.key, toggles.VOID_REQUIRES_MANAGER.key):
        client.put(f"/api/v1/settings/toggles/{key}", json={"enabled": False}, headers=owner["headers"])
    return {"owner": owner, "headers": owner["headers"], "item": item}


def _open_bill_with_two_lines(client, shop):
    table = create_table(client, shop["headers"], name=f"T{uuid.uuid4().hex[:5]}")
    order = _order(client, shop["headers"], table["id"], shop["item"]["id"], qty=1)
    _order(client, shop["headers"], table["id"], shop["item"]["id"], qty=1)
    return _bill(client, shop["headers"], order["session_id"])


def test_voiding_a_line_removes_it_from_every_total(client, shop):
    bill = _open_bill_with_two_lines(client, shop)
    assert bill["subtotal"] == 200.0
    line = bill["items"][0]

    resp = client.post(
        f"/api/v1/billing/{bill['id']}/items/{line['id']}/void",
        json={"reason": "Sent back"}, headers=shop["headers"],
    )
    assert resp.status_code == 200, resp.text
    after = resp.json()

    assert after["subtotal"] == 100.0
    assert after["grand_total"] == 100.0


def test_voided_line_is_still_returned_and_flagged(client, shop):
    bill = _open_bill_with_two_lines(client, shop)
    line = bill["items"][0]

    resp = client.post(
        f"/api/v1/billing/{bill['id']}/items/{line['id']}/void",
        json={"reason": "Rung up twice"}, headers=shop["headers"],
    )
    after = resp.json()

    voided = next(i for i in after["items"] if i["id"] == line["id"])
    assert voided["voided_at"] is not None
    assert voided["void_reason"] == "Rung up twice"
    # The line keeps its own money; only the bill's totals change.
    assert voided["line_total"] == 100.0
    assert len(after["items"]) == 2


def test_voided_line_does_not_come_back_when_the_bill_is_refreshed(client, shop):
    """The regression that makes soft-voiding necessary.

    generate_or_refresh_bill adds any order item the bill does not already
    carry. Had the void deleted the row, the next refresh — which happens
    every time another round is ordered — would silently re-add the struck
    line and the guest would be charged for it after all.
    """
    bill = _open_bill_with_two_lines(client, shop)
    line = bill["items"][0]
    client.post(
        f"/api/v1/billing/{bill['id']}/items/{line['id']}/void",
        json={"reason": "Sent back"}, headers=shop["headers"],
    )

    refreshed = _bill(client, shop["headers"], bill["session_id"])

    assert refreshed["subtotal"] == 100.0
    still_voided = next(i for i in refreshed["items"] if i["id"] == line["id"])
    assert still_voided["voided_at"] is not None


def test_voided_line_does_not_print_on_the_guest_bill(client, shop):
    bill = _open_bill_with_two_lines(client, shop)
    line = bill["items"][0]
    client.post(
        f"/api/v1/billing/{bill['id']}/items/{line['id']}/void",
        json={"reason": "Sent back"}, headers=shop["headers"],
    )

    resp = client.get(f"/api/v1/billing/{bill['id']}/receipt?format=text", headers=shop["headers"])
    assert resp.status_code == 200, resp.text
    body = resp.text

    # One line survives, so the item name appears exactly once.
    assert body.count(shop["item"]["name"]) == 1
    assert "100.00" in body


def test_tax_is_recomputed_on_the_reduced_base(client, shop):
    client.put("/api/v1/settings", json={"default_tax_percent": 5}, headers=shop["headers"])
    bill = _open_bill_with_two_lines(client, shop)
    assert bill["tax_total"] == pytest.approx(10.0)

    line = bill["items"][0]
    resp = client.post(
        f"/api/v1/billing/{bill['id']}/items/{line['id']}/void",
        json={"reason": "Sent back"}, headers=shop["headers"],
    )
    after = resp.json()

    # Tax follows the value of supply down, rather than being left on a
    # subtotal that no longer exists.
    assert after["subtotal"] == 100.0
    assert after["tax_total"] == pytest.approx(5.0)
    assert after["grand_total"] == pytest.approx(105.0)


def test_a_line_cannot_be_voided_twice(client, shop):
    bill = _open_bill_with_two_lines(client, shop)
    line = bill["items"][0]
    url = f"/api/v1/billing/{bill['id']}/items/{line['id']}/void"

    assert client.post(url, json={"reason": "Sent back"}, headers=shop["headers"]).status_code == 200
    second = client.post(url, json={"reason": "Again"}, headers=shop["headers"])
    assert second.status_code == 400
    assert "already voided" in second.json()["detail"].lower()


def test_a_line_cannot_be_voided_on_a_settled_bill(client, shop):
    bill = _open_bill_with_two_lines(client, shop)
    resp = client.post(
        "/api/v1/payments/cash",
        json={"bill_id": bill["id"], "amount": bill["grand_total"], "method": "CASH"},
        headers=shop["headers"],
    )
    assert resp.status_code == 201, resp.text

    line = bill["items"][0]
    blocked = client.post(
        f"/api/v1/billing/{bill['id']}/items/{line['id']}/void",
        json={"reason": "Too late"}, headers=shop["headers"],
    )
    assert blocked.status_code == 400
    assert "closed bill" in blocked.json()["detail"].lower()


def test_reason_is_required_when_the_toggle_is_on(client, shop):
    client.put(
        f"/api/v1/settings/toggles/{toggles.VOID_REQUIRES_REASON.key}",
        json={"enabled": True}, headers=shop["headers"],
    )
    bill = _open_bill_with_two_lines(client, shop)
    line = bill["items"][0]
    url = f"/api/v1/billing/{bill['id']}/items/{line['id']}/void"

    blocked = client.post(url, json={"reason": "   "}, headers=shop["headers"])
    assert blocked.status_code == 400
    assert "reason is required" in blocked.json()["detail"].lower()

    assert client.post(url, json={"reason": "Sent back"}, headers=shop["headers"]).status_code == 200


def test_cashier_cannot_void_a_line_when_manager_is_required(client, shop):
    """A counter that requires a manager to void a bill does not intend a
    cashier to empty that bill one line at a time."""
    client.put(
        f"/api/v1/settings/toggles/{toggles.VOID_REQUIRES_MANAGER.key}",
        json={"enabled": True}, headers=shop["headers"],
    )
    cashier = _create_staff_and_login(client, shop["headers"], "CASH_COUNTER")

    bill = _open_bill_with_two_lines(client, shop)
    line = bill["items"][0]
    url = f"/api/v1/billing/{bill['id']}/items/{line['id']}/void"

    blocked = client.post(url, json={"reason": "Sent back"}, headers=cashier)
    assert blocked.status_code == 403

    # The owner can still do it, so the bill is not stuck.
    assert client.post(url, json={"reason": "Sent back"}, headers=shop["headers"]).status_code == 200


def test_voiding_a_line_is_audited(client, shop, db_session):
    import json

    from app.models.audit import AuditLog

    bill = _open_bill_with_two_lines(client, shop)
    line = bill["items"][0]
    client.post(
        f"/api/v1/billing/{bill['id']}/items/{line['id']}/void",
        json={"reason": "Sent back"}, headers=shop["headers"],
    )

    entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "bill.item_void", AuditLog.resource_id == str(bill["id"]))
        .first()
    )
    assert entry is not None
    meta = json.loads(entry.metadata_json)
    assert meta["bill_item_id"] == line["id"]
    assert meta["reason"] == "Sent back"
    assert meta["line_total"] == 100.0
