"""Invoice numbering, void, reprint marking, and the toggles that govern them.

What is being defended: a tax invoice number must be a consecutive serial,
unique within the financial year, at most 16 characters. The old
`bill_number` satisfied none of that — its own docstring called it "a display
convenience only" — so these tests pin the properties that make the new
number a legal serial rather than another display string.
"""
import uuid

import pytest

from app.core import toggles
from app.services import invoice_service
from tests.helpers import create_category_and_item, create_table, register_and_login


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


def _settle(client, headers, bill):
    resp = client.post(
        "/api/v1/payments/cash",
        json={"bill_id": bill["id"], "amount": bill["grand_total"], "method": "CASH"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return client.get(f"/api/v1/billing/{bill['id']}", headers=headers).json()


@pytest.fixture()
def shop(client, db_session):
    owner = register_and_login(client, db_session, business_name=f"Invoice Biz {uuid.uuid4().hex[:6]}")
    _category, item = create_category_and_item(client, owner["headers"], price=100.0)
    client.put("/api/v1/settings", json={"default_tax_percent": 0, "default_service_charge_percent": 0},
               headers=owner["headers"])
    return {"owner": owner, "headers": owner["headers"], "item": item}


def _new_table(client, headers):
    return create_table(client, headers, name=f"T{uuid.uuid4().hex[:5]}")


# ---------------------------------------------------------------------------
# allocation
# ---------------------------------------------------------------------------

def test_open_bill_has_no_invoice_number_yet(client, shop):
    """The number is a legal serial, so it cannot be spent on a bill that may
    never be paid."""
    table = _new_table(client, shop["headers"])
    order = _order(client, shop["headers"], table["id"], shop["item"]["id"])
    bill = _bill(client, shop["headers"], order["session_id"])
    assert bill["invoice_number"] is None
    assert bill["bill_number"]  # internal reference still assigned immediately


def test_settling_allocates_the_number(client, shop):
    table = _new_table(client, shop["headers"])
    order = _order(client, shop["headers"], table["id"], shop["item"]["id"])
    bill = _settle(client, shop["headers"], _bill(client, shop["headers"], order["session_id"]))

    fy = invoice_service.financial_year_code()
    assert bill["invoice_number"] == f"INV/{fy}/000001"
    assert bill["finalised_at"] is not None
    assert len(bill["invoice_number"]) <= 16


def test_numbers_are_consecutive(client, shop):
    numbers = []
    for _ in range(4):
        table = _new_table(client, shop["headers"])
        order = _order(client, shop["headers"], table["id"], shop["item"]["id"])
        bill = _settle(client, shop["headers"], _bill(client, shop["headers"], order["session_id"]))
        numbers.append(bill["invoice_number"])

    fy = invoice_service.financial_year_code()
    assert numbers == [f"INV/{fy}/{n:06d}" for n in range(1, 5)]


def test_abandoned_bill_does_not_burn_a_number(client, shop):
    """The bug this design exists to prevent: a bill opened and never paid
    must not leave a hole in the series."""
    abandoned_table = _new_table(client, shop["headers"])
    abandoned_order = _order(client, shop["headers"], abandoned_table["id"], shop["item"]["id"])
    _bill(client, shop["headers"], abandoned_order["session_id"])  # never settled

    table = _new_table(client, shop["headers"])
    order = _order(client, shop["headers"], table["id"], shop["item"]["id"])
    bill = _settle(client, shop["headers"], _bill(client, shop["headers"], order["session_id"]))

    fy = invoice_service.financial_year_code()
    assert bill["invoice_number"] == f"INV/{fy}/000001"


def test_a_second_payment_does_not_allocate_a_second_number(client, shop):
    """Partial settlement then the rest: one invoice, one number."""
    table = _new_table(client, shop["headers"])
    order = _order(client, shop["headers"], table["id"], shop["item"]["id"], qty=10)  # ₹1000
    bill = _bill(client, shop["headers"], order["session_id"])

    client.post("/api/v1/payments/cash", json={"bill_id": bill["id"], "amount": 400, "method": "CASH"},
                headers=shop["headers"])
    partial = client.get(f"/api/v1/billing/{bill['id']}", headers=shop["headers"]).json()
    assert partial["status"] == "PARTIALLY_PAID"
    assert partial["invoice_number"] is None

    client.post("/api/v1/payments/cash", json={"bill_id": bill["id"], "amount": 600, "method": "CASH"},
                headers=shop["headers"])
    final = client.get(f"/api/v1/billing/{bill['id']}", headers=shop["headers"]).json()
    assert final["status"] == "PAID"
    fy = invoice_service.financial_year_code()
    assert final["invoice_number"] == f"INV/{fy}/000001"


def test_series_is_per_business(client, db_session, shop):
    """Two businesses each start at 1 — the series is theirs, not the
    platform's."""
    table = _new_table(client, shop["headers"])
    order = _order(client, shop["headers"], table["id"], shop["item"]["id"])
    a = _settle(client, shop["headers"], _bill(client, shop["headers"], order["session_id"]))

    other = register_and_login(client, db_session, business_name=f"Other Inv {uuid.uuid4().hex[:6]}")
    client.put("/api/v1/settings", json={"default_tax_percent": 0, "default_service_charge_percent": 0},
               headers=other["headers"])
    _c, other_item = create_category_and_item(client, other["headers"], price=50.0)
    other_table = create_table(client, other["headers"], name="X1")
    other_order = _order(client, other["headers"], other_table["id"], other_item["id"])
    b = _settle(client, other["headers"], _bill(client, other["headers"], other_order["session_id"]))

    assert a["invoice_number"] == b["invoice_number"]  # both ...000001
    assert a["id"] != b["id"]


def test_financial_year_code_rolls_over_on_1_april():
    from datetime import date

    assert invoice_service.financial_year_code(date(2026, 3, 31)) == "2526"
    assert invoice_service.financial_year_code(date(2026, 4, 1)) == "2627"
    assert invoice_service.financial_year_code(date(2027, 1, 15)) == "2627"


def test_number_format_fits_the_sixteen_character_limit():
    """Rule 46 caps the number at 16 characters. Six digits lands at 15, so
    there is one character of headroom rather than none."""
    assert len(invoice_service.format_invoice_number("INV", "2627", 1)) == 15
    assert len(invoice_service.format_invoice_number("INV", "2627", 999999)) == 15
    # Still legal past six digits — the format degrades gracefully.
    assert len(invoice_service.format_invoice_number("INV", "2627", 1000000)) == 16


def test_an_over_long_number_is_refused_rather_than_silently_invalid(client, shop, db_session):
    """Once the sequence needs eight digits the number passes 16 characters.
    That deserves a real decision about starting a new series, not a quietly
    non-compliant invoice."""
    from app.models.invoice import InvoiceCounter

    business_id = uuid.UUID(shop["owner"]["business_id"])
    db_session.add(InvoiceCounter(
        business_id=business_id, series="INV",
        financial_year=invoice_service.financial_year_code(), last_number=9999999,
    ))
    db_session.flush()

    with pytest.raises(ValueError, match="16-character"):
        invoice_service.allocate(db_session, business_id)


# ---------------------------------------------------------------------------
# void
# ---------------------------------------------------------------------------

def test_void_keeps_the_invoice_number(client, shop):
    """A voided invoice stays in the series. Removing it would create the
    gap the numbering rules forbid."""
    table = _new_table(client, shop["headers"])
    order = _order(client, shop["headers"], table["id"], shop["item"]["id"])
    bill = _settle(client, shop["headers"], _bill(client, shop["headers"], order["session_id"]))
    number = bill["invoice_number"]

    resp = client.post(f"/api/v1/billing/{bill['id']}/void",
                       json={"reason": "Guest disputed the order"}, headers=shop["headers"])
    assert resp.status_code == 200, resp.text
    voided = resp.json()
    assert voided["status"] == "CANCELLED"
    assert voided["invoice_number"] == number
    assert voided["void_reason"] == "Guest disputed the order"
    assert voided["voided_at"] is not None


def test_void_does_not_free_the_number_for_reuse(client, shop):
    table = _new_table(client, shop["headers"])
    order = _order(client, shop["headers"], table["id"], shop["item"]["id"])
    first = _settle(client, shop["headers"], _bill(client, shop["headers"], order["session_id"]))
    client.post(f"/api/v1/billing/{first['id']}/void", json={"reason": "mistake"}, headers=shop["headers"])

    table2 = _new_table(client, shop["headers"])
    order2 = _order(client, shop["headers"], table2["id"], shop["item"]["id"])
    second = _settle(client, shop["headers"], _bill(client, shop["headers"], order2["session_id"]))

    assert second["invoice_number"] != first["invoice_number"]
    fy = invoice_service.financial_year_code()
    assert second["invoice_number"] == f"INV/{fy}/000002"


def test_void_requires_a_reason_by_default(client, shop):
    table = _new_table(client, shop["headers"])
    order = _order(client, shop["headers"], table["id"], shop["item"]["id"])
    bill = _bill(client, shop["headers"], order["session_id"])

    resp = client.post(f"/api/v1/billing/{bill['id']}/void", json={}, headers=shop["headers"])
    assert resp.status_code == 400
    assert "reason" in resp.text.lower()


def test_voiding_twice_is_refused(client, shop):
    table = _new_table(client, shop["headers"])
    order = _order(client, shop["headers"], table["id"], shop["item"]["id"])
    bill = _bill(client, shop["headers"], order["session_id"])
    client.post(f"/api/v1/billing/{bill['id']}/void", json={"reason": "x"}, headers=shop["headers"])
    again = client.post(f"/api/v1/billing/{bill['id']}/void", json={"reason": "x"}, headers=shop["headers"])
    assert again.status_code == 400


# ---------------------------------------------------------------------------
# reprint
# ---------------------------------------------------------------------------

def test_first_print_is_original_and_the_rest_are_duplicates(client, shop):
    """The oldest till trick is printing two 'originals' of one bill."""
    table = _new_table(client, shop["headers"])
    order = _order(client, shop["headers"], table["id"], shop["item"]["id"])
    bill = _settle(client, shop["headers"], _bill(client, shop["headers"], order["session_id"]))

    first = client.post(f"/api/v1/billing/{bill['id']}/print", headers=shop["headers"]).json()
    assert first["is_duplicate"] is False
    assert first["print_count"] == 1

    second = client.post(f"/api/v1/billing/{bill['id']}/print", headers=shop["headers"]).json()
    assert second["is_duplicate"] is True
    assert second["print_count"] == 2


# ---------------------------------------------------------------------------
# toggles actually change server behaviour
# ---------------------------------------------------------------------------

def test_toggles_are_listed_with_defaults_and_not_marked_as_chosen(client, shop):
    resp = client.get("/api/v1/settings/toggles", headers=shop["headers"])
    assert resp.status_code == 200
    by_key = {t["key"]: t for t in resp.json()}
    assert by_key[toggles.VOID_REQUIRES_REASON.key]["enabled"] is True
    assert by_key[toggles.VOID_REQUIRES_REASON.key]["is_overridden"] is False


def test_turning_off_the_reason_requirement_changes_the_api(client, shop):
    """The point of a toggle: it must change what the server does, not just
    what the screen shows."""
    resp = client.put(f"/api/v1/settings/toggles/{toggles.VOID_REQUIRES_REASON.key}",
                      json={"enabled": False}, headers=shop["headers"])
    assert resp.status_code == 200
    assert resp.json()["is_overridden"] is True

    table = _new_table(client, shop["headers"])
    order = _order(client, shop["headers"], table["id"], shop["item"]["id"])
    bill = _bill(client, shop["headers"], order["session_id"])
    voided = client.post(f"/api/v1/billing/{bill['id']}/void", json={}, headers=shop["headers"])
    assert voided.status_code == 200


def test_turning_off_duplicate_marking_changes_the_api(client, shop):
    client.put(f"/api/v1/settings/toggles/{toggles.MARK_DUPLICATE_REPRINT.key}",
               json={"enabled": False}, headers=shop["headers"])

    table = _new_table(client, shop["headers"])
    order = _order(client, shop["headers"], table["id"], shop["item"]["id"])
    bill = _settle(client, shop["headers"], _bill(client, shop["headers"], order["session_id"]))

    client.post(f"/api/v1/billing/{bill['id']}/print", headers=shop["headers"])
    second = client.post(f"/api/v1/billing/{bill['id']}/print", headers=shop["headers"]).json()
    assert second["print_count"] == 2
    assert second["is_duplicate"] is False


def test_continuous_series_toggle_drops_the_year_from_the_number(client, shop):
    client.put(f"/api/v1/settings/toggles/{toggles.INVOICE_SERIES_PER_YEAR.key}",
               json={"enabled": False}, headers=shop["headers"])

    table = _new_table(client, shop["headers"])
    order = _order(client, shop["headers"], table["id"], shop["item"]["id"])
    bill = _settle(client, shop["headers"], _bill(client, shop["headers"], order["session_id"]))
    assert bill["invoice_number"] == "INV/000001"


def test_resetting_a_toggle_returns_it_to_the_default(client, shop):
    key = toggles.VOID_REQUIRES_REASON.key
    client.put(f"/api/v1/settings/toggles/{key}", json={"enabled": False}, headers=shop["headers"])
    resp = client.delete(f"/api/v1/settings/toggles/{key}", headers=shop["headers"])
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True
    assert resp.json()["is_overridden"] is False


def test_unknown_toggle_key_is_rejected(client, shop):
    resp = client.put("/api/v1/settings/toggles/billing.not_a_real_switch",
                      json={"enabled": False}, headers=shop["headers"])
    assert resp.status_code == 404


def test_non_owner_cannot_change_a_toggle(client, db_session, shop):
    resp = client.post(
        "/api/v1/staff",
        json={
            "first_name": "Cash", "last_name": "One",
            "email": f"cash-{uuid.uuid4().hex[:8]}@example.com",
            "mobile": f"9{uuid.uuid4().int % 10**9:09d}",
            "role": "CASH_COUNTER", "password": "CounterPass123",
        },
        headers=shop["headers"],
    )
    assert resp.status_code == 201, resp.text
    login = client.post("/api/v1/auth/login",
                        json={"identifier": resp.json()["email"], "password": "CounterPass123"})
    staff_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Readable — the UI needs it to render correctly.
    assert client.get("/api/v1/settings/toggles", headers=staff_headers).status_code == 200
    # Not writable.
    blocked = client.put(f"/api/v1/settings/toggles/{toggles.VOID_REQUIRES_REASON.key}",
                         json={"enabled": False}, headers=staff_headers)
    assert blocked.status_code == 403


def test_entitlement_toggles_are_refused_for_owners(client, shop, monkeypatch):
    """An owner who can flip their own entitlements makes "pay only for what
    you need" meaningless, so the refusal is enforced server-side."""
    from app.core.toggles import ToggleDef, ToggleGroup, _REGISTRY

    entitlement = ToggleDef(
        key="billing.test_entitlement", group=ToggleGroup.BILLING, default=False,
        owner_editable=False, label="Plan-controlled thing", description="test",
    )
    monkeypatch.setitem(_REGISTRY, entitlement.key, entitlement)

    resp = client.put(f"/api/v1/settings/toggles/{entitlement.key}",
                      json={"enabled": True}, headers=shop["headers"])
    assert resp.status_code == 403
    assert "plan" in resp.text.lower()


def test_invoice_series_endpoint_shows_the_next_number(client, shop):
    resp = client.get("/api/v1/settings/invoice-series", headers=shop["headers"])
    assert resp.status_code == 200
    body = resp.json()
    fy = invoice_service.financial_year_code()
    assert body["next_number"] == f"INV/{fy}/000001"
    assert body["last_issued"] == 0


# ---------------------------------------------------------------------------
# concurrency — the reason allocation takes a row lock
# ---------------------------------------------------------------------------

def test_concurrent_allocations_do_not_collide(client, shop):
    """Two cashiers pressing Settle at the same instant must not receive the
    same serial.

    Uses real threads against real sessions rather than the transaction-bound
    test session, because the behaviour under test is a database row lock —
    a single-session test would prove nothing about it.
    """
    import threading

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as RawSession

    from tests.conftest import TEST_DATABASE_URL

    business_id = uuid.UUID(shop["owner"]["business_id"])
    engine = create_engine(TEST_DATABASE_URL, future=True)

    # The fixture's business lives in a rolled-back transaction, so it is
    # invisible to other connections. Allocate against a standalone business
    # row created (and cleaned up) on the same connections the threads use.
    setup = RawSession(bind=engine, future=True)
    from app.models.business import Business

    biz = Business(name=f"Concurrency {uuid.uuid4().hex[:6]}",
                   slug=f"concurrency-{uuid.uuid4().hex[:8]}", business_type="RESTAURANT")
    setup.add(biz)
    setup.commit()
    business_id = biz.id
    setup.close()

    results: list[str] = []
    errors: list[Exception] = []
    lock = threading.Lock()
    start = threading.Barrier(8)

    def allocate_one():
        session = RawSession(bind=engine, future=True)
        try:
            start.wait(timeout=10)
            number, *_ = invoice_service.allocate(session, business_id)
            session.commit()
            with lock:
                results.append(number)
        except Exception as exc:  # noqa: BLE001
            with lock:
                errors.append(exc)
            session.rollback()
        finally:
            session.close()

    threads = [threading.Thread(target=allocate_one) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    cleanup = RawSession(bind=engine, future=True)
    cleanup.query(Business).filter(Business.id == business_id).delete()
    cleanup.commit()
    cleanup.close()
    engine.dispose()

    assert not errors, errors
    assert len(results) == 8
    # The property that matters: eight allocations, eight distinct numbers,
    # and no gaps between them.
    assert len(set(results)) == 8, f"duplicate serials issued: {sorted(results)}"
    sequences = sorted(int(n.rsplit("/", 1)[1]) for n in results)
    assert sequences == list(range(1, 9)), sequences
