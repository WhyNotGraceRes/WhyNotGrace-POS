"""Complimentary lines, and no-charge bills.

The distinction being defended here is between a void and a comp. Both stop
a line being charged, and it would be easy to implement one as the other —
but they are different claims. A void says the dish was never supplied, so it
leaves the guest's bill. A comp says it was supplied and given away, so it
stays on the bill marked NC and the value given remains countable.
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


@pytest.fixture()
def shop(client, db_session):
    owner = register_and_login(client, db_session, business_name=f"Comp Biz {uuid.uuid4().hex[:6]}")
    _category, item = create_category_and_item(client, owner["headers"], price=100.0)
    client.put(
        "/api/v1/settings",
        json={"default_tax_percent": 0, "default_service_charge_percent": 0},
        headers=owner["headers"],
    )
    for key in (
        toggles.COMP_REQUIRES_REASON.key, toggles.COMP_REQUIRES_MANAGER.key,
        toggles.VOID_REQUIRES_REASON.key, toggles.VOID_REQUIRES_MANAGER.key,
    ):
        client.put(f"/api/v1/settings/toggles/{key}", json={"enabled": False}, headers=owner["headers"])
    return {"owner": owner, "headers": owner["headers"], "item": item}


def _open_bill(client, shop, lines=2):
    table = create_table(client, shop["headers"], name=f"T{uuid.uuid4().hex[:5]}")
    order = _order(client, shop["headers"], table["id"], shop["item"]["id"], qty=1)
    for _ in range(lines - 1):
        _order(client, shop["headers"], table["id"], shop["item"]["id"], qty=1)
    resp = client.post("/api/v1/billing/generate", json={"session_id": order["session_id"]}, headers=shop["headers"])
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- comping a single line -------------------------------------------------


def test_comping_a_line_removes_its_money_but_keeps_the_line(client, shop):
    bill = _open_bill(client, shop)
    assert bill["subtotal"] == 200.0
    line = bill["items"][0]

    resp = client.post(
        f"/api/v1/billing/{bill['id']}/items/{line['id']}/comp",
        json={"reason": "Regular guest, birthday"}, headers=shop["headers"],
    )
    assert resp.status_code == 200, resp.text
    after = resp.json()

    assert after["subtotal"] == 100.0
    assert after["grand_total"] == 100.0

    comped = next(i for i in after["items"] if i["id"] == line["id"])
    assert comped["comped_at"] is not None
    assert comped["comp_reason"] == "Regular guest, birthday"
    # The line keeps its price: what was given away has to stay countable.
    assert comped["line_total"] == 100.0


def test_a_comped_line_prints_marked_nc_unlike_a_voided_one(client, shop):
    """The distinction that justifies comp existing separately from void."""
    bill = _open_bill(client, shop, lines=3)
    comped, voided = bill["items"][0], bill["items"][1]

    client.post(
        f"/api/v1/billing/{bill['id']}/items/{comped['id']}/comp",
        json={"reason": "On the house"}, headers=shop["headers"],
    )
    client.post(
        f"/api/v1/billing/{bill['id']}/items/{voided['id']}/void",
        json={"reason": "Never made"}, headers=shop["headers"],
    )

    body = client.get(f"/api/v1/billing/{bill['id']}/receipt?format=text", headers=shop["headers"]).text

    # Three lines ordered, one voided away: two print.
    assert body.count(shop["item"]["name"]) == 2
    assert "NC" in body
    # Only the one chargeable line is billed.
    assert "100.00" in body


def test_tax_falls_with_a_comped_line(client, shop):
    client.put("/api/v1/settings", json={"default_tax_percent": 5}, headers=shop["headers"])
    bill = _open_bill(client, shop)
    assert bill["tax_total"] == pytest.approx(10.0)

    line = bill["items"][0]
    after = client.post(
        f"/api/v1/billing/{bill['id']}/items/{line['id']}/comp",
        json={"reason": "On the house"}, headers=shop["headers"],
    ).json()

    # Food given away carries no consideration, so it is not part of the
    # value of supply and must not be taxed.
    assert after["subtotal"] == 100.0
    assert after["tax_total"] == pytest.approx(5.0)
    assert after["grand_total"] == pytest.approx(105.0)


def test_a_comp_can_be_reversed_but_a_void_cannot(client, shop):
    bill = _open_bill(client, shop)
    line = bill["items"][0]

    client.post(
        f"/api/v1/billing/{bill['id']}/items/{line['id']}/comp",
        json={"reason": "Mistake"}, headers=shop["headers"],
    )
    resp = client.post(
        f"/api/v1/billing/{bill['id']}/items/{line['id']}/uncomp", json={}, headers=shop["headers"]
    )
    assert resp.status_code == 200, resp.text
    after = resp.json()

    assert after["subtotal"] == 200.0
    restored = next(i for i in after["items"] if i["id"] == line["id"])
    assert restored["comped_at"] is None

    # There is no equivalent for a void: no /unvoid route exists.
    assert client.post(
        f"/api/v1/billing/{bill['id']}/items/{line['id']}/unvoid", json={}, headers=shop["headers"]
    ).status_code == 404


def test_a_voided_line_cannot_be_comped(client, shop):
    """A dish that was never supplied cannot be given away."""
    bill = _open_bill(client, shop)
    line = bill["items"][0]
    client.post(
        f"/api/v1/billing/{bill['id']}/items/{line['id']}/void",
        json={"reason": "Never made"}, headers=shop["headers"],
    )

    blocked = client.post(
        f"/api/v1/billing/{bill['id']}/items/{line['id']}/comp",
        json={"reason": "On the house"}, headers=shop["headers"],
    )
    assert blocked.status_code == 400
    assert "voided" in blocked.json()["detail"].lower()


def test_comp_toggles_are_separate_from_the_void_toggles(client, shop):
    """A counter may let a cashier strike an unmade dish while still
    insisting a manager signs off anything given away."""
    client.put(
        f"/api/v1/settings/toggles/{toggles.COMP_REQUIRES_MANAGER.key}",
        json={"enabled": True}, headers=shop["headers"],
    )
    cashier = _create_staff_and_login(client, shop["headers"], "CASH_COUNTER")
    bill = _open_bill(client, shop)
    first, second = bill["items"][0], bill["items"][1]

    # Void is still open to the cashier, because its own toggle is off.
    assert client.post(
        f"/api/v1/billing/{bill['id']}/items/{first['id']}/void",
        json={"reason": "Never made"}, headers=cashier,
    ).status_code == 200

    blocked = client.post(
        f"/api/v1/billing/{bill['id']}/items/{second['id']}/comp",
        json={"reason": "On the house"}, headers=cashier,
    )
    assert blocked.status_code == 403


def test_comp_reason_is_required_when_the_toggle_is_on(client, shop):
    client.put(
        f"/api/v1/settings/toggles/{toggles.COMP_REQUIRES_REASON.key}",
        json={"enabled": True}, headers=shop["headers"],
    )
    bill = _open_bill(client, shop)
    line = bill["items"][0]
    url = f"/api/v1/billing/{bill['id']}/items/{line['id']}/comp"

    blocked = client.post(url, json={"reason": "  "}, headers=shop["headers"])
    assert blocked.status_code == 400
    assert "reason is required" in blocked.json()["detail"].lower()

    assert client.post(url, json={"reason": "On the house"}, headers=shop["headers"]).status_code == 200


# --- no-charge bills -------------------------------------------------------


def test_no_charge_bill_settles_at_zero_with_every_line_comped(client, shop):
    bill = _open_bill(client, shop)

    resp = client.post(
        f"/api/v1/billing/{bill['id']}/no-charge",
        json={"reason": "Staff meal"}, headers=shop["headers"],
    )
    assert resp.status_code == 200, resp.text
    after = resp.json()

    assert after["nc_at"] is not None
    assert after["nc_reason"] == "Staff meal"
    assert after["subtotal"] == 0.0
    assert after["grand_total"] == 0.0
    assert after["status"] == "PAID"
    assert all(i["comped_at"] is not None for i in after["items"])


def test_no_charge_bill_takes_no_payment_and_no_invoice_number(client, shop, db_session):
    """Two deliberate omissions.

    A zero-rupee CASH payment would put a fictional row into the shift's
    takings and onto the Z-report. And the invoice series is the GST serial —
    food given away is not a taxable supply, so burning a serial on it would
    put a zero-value invoice into the return.
    """
    from app.models.payment import Payment

    bill = _open_bill(client, shop)
    after = client.post(
        f"/api/v1/billing/{bill['id']}/no-charge",
        json={"reason": "Staff meal"}, headers=shop["headers"],
    ).json()

    assert after["amount_paid"] == 0.0
    assert after["invoice_number"] is None

    payments = db_session.query(Payment).filter(Payment.bill_id == uuid.UUID(bill["id"])).all()
    assert payments == []


def test_no_charge_bill_prints_as_a_no_charge_document(client, shop):
    bill = _open_bill(client, shop)
    client.post(
        f"/api/v1/billing/{bill['id']}/no-charge",
        json={"reason": "Staff meal"}, headers=shop["headers"],
    )

    body = client.get(f"/api/v1/billing/{bill['id']}/receipt?format=text", headers=shop["headers"]).text

    assert "NO CHARGE" in body
    assert "Staff meal" in body
    # The lines are still on the paper, priced, so what was given is legible.
    assert body.count(shop["item"]["name"]) == 2
    assert "NC" in body


def test_no_charge_is_refused_once_money_has_been_taken(client, shop):
    bill = _open_bill(client, shop)
    resp = client.post(
        "/api/v1/payments/cash",
        json={"bill_id": bill["id"], "amount": 50, "method": "CASH"},
        headers=shop["headers"],
    )
    assert resp.status_code == 201, resp.text

    blocked = client.post(
        f"/api/v1/billing/{bill['id']}/no-charge",
        json={"reason": "Staff meal"}, headers=shop["headers"],
    )
    assert blocked.status_code == 400
    assert "refund" in blocked.json()["detail"].lower()


def test_no_charge_leaves_a_voided_line_voided(client, shop):
    """A line that was never supplied is not part of what is being given."""
    bill = _open_bill(client, shop)
    voided = bill["items"][0]
    client.post(
        f"/api/v1/billing/{bill['id']}/items/{voided['id']}/void",
        json={"reason": "Never made"}, headers=shop["headers"],
    )

    after = client.post(
        f"/api/v1/billing/{bill['id']}/no-charge",
        json={"reason": "Staff meal"}, headers=shop["headers"],
    ).json()

    still_voided = next(i for i in after["items"] if i["id"] == voided["id"])
    assert still_voided["voided_at"] is not None
    assert still_voided["comped_at"] is None


def test_no_charge_is_audited_with_the_value_given_away(client, shop, db_session):
    import json

    from app.models.audit import AuditLog

    bill = _open_bill(client, shop)
    client.post(
        f"/api/v1/billing/{bill['id']}/no-charge",
        json={"reason": "Staff meal"}, headers=shop["headers"],
    )

    entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "bill.no_charge", AuditLog.resource_id == str(bill["id"]))
        .first()
    )
    assert entry is not None
    meta = json.loads(entry.metadata_json)
    assert meta["reason"] == "Staff meal"
    # The number an owner reviewing giveaways actually wants.
    assert meta["value_given"] == 200.0


def test_cashier_cannot_mark_a_bill_no_charge_when_manager_is_required(client, shop):
    client.put(
        f"/api/v1/settings/toggles/{toggles.COMP_REQUIRES_MANAGER.key}",
        json={"enabled": True}, headers=shop["headers"],
    )
    cashier = _create_staff_and_login(client, shop["headers"], "CASH_COUNTER")
    bill = _open_bill(client, shop)

    blocked = client.post(
        f"/api/v1/billing/{bill['id']}/no-charge",
        json={"reason": "Staff meal"}, headers=cashier,
    )
    assert blocked.status_code == 403

    assert client.post(
        f"/api/v1/billing/{bill['id']}/no-charge",
        json={"reason": "Staff meal"}, headers=shop["headers"],
    ).status_code == 200
