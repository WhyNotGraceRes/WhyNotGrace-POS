"""Cash drawer accounting.

This is the feature an owner buys a POS for, so the arithmetic has to be
exactly right and the control has to actually control something. The two
things being defended:

  * the expected figure counts cash and only cash, adjusted for what went
    back out, because a cashier cannot be asked to account for money that
    never entered the drawer
  * blind counting genuinely withholds the expected figure until a count has
    been committed, since a cashier shown it first will type it back
"""
import uuid

import pytest

from app.core import toggles
from tests.helpers import create_category_and_item, create_table, register_and_login


def _order(client, headers, table_id, item_id, qty=1):
    resp = client.post(
        "/api/v1/orders",
        json={"location_id": table_id, "source": "DINE_IN", "pricing_context": "DINE_IN",
              "items": [{"menu_item_id": item_id, "variant_id": None, "quantity": qty, "option_ids": []}]},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture()
def counter(client, db_session):
    owner = register_and_login(client, db_session, business_name=f"Shift Biz {uuid.uuid4().hex[:6]}")
    client.put("/api/v1/settings",
               json={"default_tax_percent": 0, "default_service_charge_percent": 0},
               headers=owner["headers"])
    _c, item = create_category_and_item(client, owner["headers"], price=100.0)
    return {"owner": owner, "headers": owner["headers"], "item": item}


def _settle(client, counter, amount=None, method="CASH", qty=1):
    """Sells one item and pays for it, returning the bill."""
    table = create_table(client, counter["headers"], name=f"T{uuid.uuid4().hex[:5]}")
    order = _order(client, counter["headers"], table["id"], counter["item"]["id"], qty=qty)
    bill = client.post("/api/v1/billing/generate", json={"session_id": order["session_id"]},
                       headers=counter["headers"]).json()
    resp = client.post("/api/v1/payments/cash",
                       json={"bill_id": bill["id"],
                             "amount": amount if amount is not None else bill["grand_total"],
                             "method": method},
                       headers=counter["headers"])
    assert resp.status_code == 201, resp.text
    return bill, resp.json()


def _open(client, counter, opening_float=500):
    resp = client.post("/api/v1/shifts", json={"opening_float": opening_float},
                       headers=counter["headers"])
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# opening and closing
# ---------------------------------------------------------------------------

def test_no_open_shift_initially(client, counter):
    resp = client.get("/api/v1/shifts/current", headers=counter["headers"])
    assert resp.status_code == 200
    assert resp.json() is None


def test_open_then_current_returns_it(client, counter):
    shift = _open(client, counter, 500)
    assert shift["status"] == "OPEN"
    assert shift["opening_float"] == 500.0

    current = client.get("/api/v1/shifts/current", headers=counter["headers"]).json()
    assert current["id"] == shift["id"]


def test_one_open_shift_per_user(client, counter):
    """Two open drawers for one person means every payment has to guess which
    it belongs to."""
    _open(client, counter)
    again = client.post("/api/v1/shifts", json={"opening_float": 200}, headers=counter["headers"])
    assert again.status_code == 400
    assert "already have an open shift" in again.text


def test_closing_twice_is_refused(client, counter):
    shift = _open(client, counter)
    client.post(f"/api/v1/shifts/{shift['id']}/close", json={"declared_cash": 500},
                headers=counter["headers"])
    again = client.post(f"/api/v1/shifts/{shift['id']}/close", json={"declared_cash": 500},
                        headers=counter["headers"])
    assert again.status_code == 400


def test_closing_frees_the_user_to_open_another(client, counter):
    first = _open(client, counter)
    client.post(f"/api/v1/shifts/{first['id']}/close", json={"declared_cash": 500},
                headers=counter["headers"])
    second = _open(client, counter, 300)
    assert second["id"] != first["id"]


# ---------------------------------------------------------------------------
# the arithmetic
# ---------------------------------------------------------------------------

def test_expected_cash_is_float_plus_takings(client, counter):
    shift = _open(client, counter, 500)
    _settle(client, counter, qty=2)   # ₹200 cash

    report = client.post(f"/api/v1/shifts/{shift['id']}/close",
                         json={"declared_cash": 700}, headers=counter["headers"]).json()
    assert report["opening_float"] == 500.0
    assert report["cash_taken"] == 200.0
    assert report["expected_cash"] == 700.0
    assert report["variance"] == 0.0


def test_shortfall_and_surplus_have_the_right_sign(client, counter):
    shift = _open(client, counter, 500)
    _settle(client, counter, qty=2)   # expected 700

    short = client.post(f"/api/v1/shifts/{shift['id']}/close",
                        json={"declared_cash": 650}, headers=counter["headers"]).json()
    assert short["variance"] == -50.0   # negative is missing money

    shift2 = _open(client, counter, 100)
    over = client.post(f"/api/v1/shifts/{shift2['id']}/close",
                       json={"declared_cash": 130}, headers=counter["headers"]).json()
    assert over["variance"] == 30.0


def test_only_cash_counts_toward_the_drawer(client, counter):
    """A card or UPI payment never enters the drawer, so counting it would
    produce an expected figure no honest cashier could match."""
    shift = _open(client, counter, 500)
    _settle(client, counter, qty=1, method="CASH")   # ₹100
    _settle(client, counter, qty=3, method="CARD")   # ₹300, not in the drawer

    report = client.post(f"/api/v1/shifts/{shift['id']}/close",
                         json={"declared_cash": 600}, headers=counter["headers"]).json()
    assert report["cash_taken"] == 100.0
    assert report["expected_cash"] == 600.0
    assert report["variance"] == 0.0
    # Gross takings still include the card sale — the drawer is not the till.
    assert report["gross_takings"] == 400.0
    methods = {p["method"]: p["amount"] for p in report["payments"]}
    assert methods == {"CASH": 100.0, "CARD": 300.0}


def test_cash_refunds_come_out_of_the_drawer(client, counter):
    shift = _open(client, counter, 500)
    _bill, payment = _settle(client, counter, qty=2)   # +₹200

    resp = client.post("/api/v1/payments/refund",
                       json={"payment_id": payment["id"], "amount": 50, "method": "CASH"},
                       headers=counter["headers"])
    assert resp.status_code == 201, resp.text

    report = client.post(f"/api/v1/shifts/{shift['id']}/close",
                         json={"declared_cash": 650}, headers=counter["headers"]).json()
    assert report["cash_returned"] == 50.0
    assert report["expected_cash"] == 650.0
    assert report["variance"] == 0.0
    assert report["refunds_count"] == 1


def test_a_refund_paid_by_upi_does_not_touch_the_drawer(client, counter):
    shift = _open(client, counter, 500)
    _bill, payment = _settle(client, counter, qty=2)

    client.post("/api/v1/payments/refund",
                json={"payment_id": payment["id"], "amount": 50, "method": "UPI"},
                headers=counter["headers"])

    report = client.post(f"/api/v1/shifts/{shift['id']}/close",
                         json={"declared_cash": 700}, headers=counter["headers"]).json()
    assert report["cash_returned"] == 0.0
    assert report["expected_cash"] == 700.0


def test_payments_belong_to_the_shift_open_when_they_happened(client, counter):
    """Scoped by shift_id, not by a time window — a payment recorded a second
    after close would otherwise land in the wrong drawer."""
    first = _open(client, counter, 100)
    _settle(client, counter, qty=1)   # ₹100 into the first drawer
    client.post(f"/api/v1/shifts/{first['id']}/close", json={"declared_cash": 200},
                headers=counter["headers"])

    second = _open(client, counter, 100)
    _settle(client, counter, qty=5)   # ₹500 into the second

    first_report = client.get(f"/api/v1/shifts/{first['id']}/report",
                              headers=counter["headers"]).json()
    second_report = client.post(f"/api/v1/shifts/{second['id']}/close",
                                json={"declared_cash": 600}, headers=counter["headers"]).json()

    assert first_report["cash_taken"] == 100.0
    assert second_report["cash_taken"] == 500.0


def test_payments_with_no_shift_open_are_not_attributed(client, counter):
    """They still succeed — a missing drawer must never block taking money —
    but they belong to no shift, which is the gap the require-shift toggle
    exists to close."""
    _settle(client, counter, qty=2)
    shift = _open(client, counter, 0)
    report = client.post(f"/api/v1/shifts/{shift['id']}/close",
                         json={"declared_cash": 0}, headers=counter["headers"]).json()
    assert report["cash_taken"] == 0.0
    assert report["bills_settled"] == 0


# ---------------------------------------------------------------------------
# blind counting — the actual control
# ---------------------------------------------------------------------------

def test_expected_cash_is_hidden_while_the_shift_is_open(client, counter):
    """A cashier shown the expected amount will type it back, which is the
    difference between a cash control and a formality."""
    shift = _open(client, counter, 500)
    _settle(client, counter, qty=2)

    report = client.get(f"/api/v1/shifts/{shift['id']}/report", headers=counter["headers"]).json()
    assert report["blind_count"] is True
    assert report["expected_cash"] is None
    # Everything else stays visible — this hides one number, not the report.
    assert report["cash_taken"] == 200.0


def test_expected_cash_appears_once_the_count_is_committed(client, counter):
    shift = _open(client, counter, 500)
    _settle(client, counter, qty=2)

    closed = client.post(f"/api/v1/shifts/{shift['id']}/close",
                         json={"declared_cash": 690}, headers=counter["headers"]).json()
    assert closed["expected_cash"] == 700.0
    assert closed["declared_cash"] == 690.0
    assert closed["variance"] == -10.0


def test_turning_blind_counting_off_reveals_it_early(client, counter):
    client.put(f"/api/v1/settings/toggles/{toggles.BLIND_CASH_COUNT.key}",
               json={"enabled": False}, headers=counter["headers"])

    shift = _open(client, counter, 500)
    _settle(client, counter, qty=2)

    report = client.get(f"/api/v1/shifts/{shift['id']}/report", headers=counter["headers"]).json()
    assert report["blind_count"] is False
    assert report["expected_cash"] == 700.0


# ---------------------------------------------------------------------------
# requiring a shift
# ---------------------------------------------------------------------------

def test_payment_is_refused_with_no_shift_when_required(client, counter):
    client.put(f"/api/v1/settings/toggles/{toggles.REQUIRE_SHIFT_FOR_PAYMENT.key}",
               json={"enabled": True}, headers=counter["headers"])

    table = create_table(client, counter["headers"], name=f"T{uuid.uuid4().hex[:5]}")
    order = _order(client, counter["headers"], table["id"], counter["item"]["id"])
    bill = client.post("/api/v1/billing/generate", json={"session_id": order["session_id"]},
                       headers=counter["headers"]).json()

    blocked = client.post("/api/v1/payments/cash",
                          json={"bill_id": bill["id"], "amount": bill["grand_total"], "method": "CASH"},
                          headers=counter["headers"])
    assert blocked.status_code == 400
    assert "Open a shift" in blocked.text

    _open(client, counter, 0)
    allowed = client.post("/api/v1/payments/cash",
                          json={"bill_id": bill["id"], "amount": bill["grand_total"], "method": "CASH"},
                          headers=counter["headers"])
    assert allowed.status_code == 201


# ---------------------------------------------------------------------------
# exceptions an owner scans for
# ---------------------------------------------------------------------------

def test_report_surfaces_voids_and_discounts(client, counter):
    """A drawer that balances perfectly while ten bills were voided is not a
    drawer that balanced."""
    shift = _open(client, counter, 0)

    # The discount has to go on before settlement — a paid bill refuses
    # modification, which is itself correct.
    table = create_table(client, counter["headers"], name=f"T{uuid.uuid4().hex[:5]}")
    order = _order(client, counter["headers"], table["id"], counter["item"]["id"], qty=2)
    bill = client.post("/api/v1/billing/generate", json={"session_id": order["session_id"]},
                       headers=counter["headers"]).json()

    discounted = client.post(f"/api/v1/billing/{bill['id']}/discount",
                             json={"name": "Regular", "amount": 10}, headers=counter["headers"])
    assert discounted.status_code == 200, discounted.text

    paid = client.post("/api/v1/payments/cash",
                       json={"bill_id": bill["id"], "amount": discounted.json()["grand_total"],
                             "method": "CASH"},
                       headers=counter["headers"])
    assert paid.status_code == 201, paid.text

    voided = client.post(f"/api/v1/billing/{bill['id']}/void",
                         json={"reason": "Guest complaint"}, headers=counter["headers"])
    assert voided.status_code == 200, voided.text

    report = client.get(f"/api/v1/shifts/{shift['id']}/report", headers=counter["headers"]).json()
    assert report["bills_settled"] == 1
    assert report["bills_voided"] == 1
    assert report["discounts_total"] == 10.0


# ---------------------------------------------------------------------------
# printing
# ---------------------------------------------------------------------------

def test_shift_report_prints_on_the_same_paper_as_bills(client, counter):
    shift = _open(client, counter, 500)
    _settle(client, counter, qty=2)
    client.post(f"/api/v1/shifts/{shift['id']}/close", json={"declared_cash": 690},
                headers=counter["headers"])

    body = client.get(f"/api/v1/shifts/{shift['id']}/report/print",
                      params={"format": "text"}, headers=counter["headers"]).text
    assert "SHIFT REPORT" in body
    assert "Opening float" in body
    assert "700.00" in body      # expected
    assert "690.00" in body      # counted
    assert "SHORT" in body       # the line an owner actually reads


def test_printing_an_open_shift_does_not_leak_the_expected_figure(client, counter):
    """Otherwise printing would be a way around the blind count."""
    shift = _open(client, counter, 500)
    _settle(client, counter, qty=2)

    body = client.get(f"/api/v1/shifts/{shift['id']}/report/print",
                      params={"format": "text"}, headers=counter["headers"]).text
    assert "(counted at close)" in body
    assert "700.00" not in body
