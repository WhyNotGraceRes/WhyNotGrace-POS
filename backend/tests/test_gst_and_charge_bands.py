"""GST arithmetic and owner-defined charge bands.

The two bugs pinned here were found by running a real bill, not by reading
code, and both moved real money:

  * a discount reduced what the guest paid but not what they were taxed on
  * the service charge was never included in the taxable value

Every number below is asserted explicitly rather than recomputed from the
same formula the code uses, so a future change to that formula fails these
tests instead of silently agreeing with itself.
"""
import uuid

import pytest

from tests.helpers import create_category_and_item, create_table, register_and_login


def _settings(client, headers, **kw):
    resp = client.put("/api/v1/settings", json=kw, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _order(client, headers, table_id, item_id, qty):
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
    owner = register_and_login(client, db_session, business_name=f"Tax Biz {uuid.uuid4().hex[:6]}")
    _category, item = create_category_and_item(client, owner["headers"], price=100.0)
    table = create_table(client, owner["headers"], name=f"T{uuid.uuid4().hex[:4]}")
    return {"owner": owner, "headers": owner["headers"], "item": item, "table": table}


# ---------------------------------------------------------------------------
# the two bugs
# ---------------------------------------------------------------------------

def test_discount_reduces_the_taxable_value(client, shop):
    """Bug 1. GST is due on the value after a discount shown on the invoice.
    Taxing the pre-discount subtotal over-charges the guest and
    over-remits to the government."""
    _settings(client, shop["headers"], default_tax_percent=5, default_service_charge_percent=0)
    order = _order(client, shop["headers"], shop["table"]["id"], shop["item"]["id"], 10)  # ₹1000
    bill = _bill(client, shop["headers"], order["session_id"])
    assert bill["subtotal"] == 1000.0
    assert bill["tax_total"] == 50.0

    resp = client.post(f"/api/v1/billing/{bill['id']}/discount",
                       json={"name": "Regular guest", "amount": 200}, headers=shop["headers"])
    assert resp.status_code == 200, resp.text
    after = resp.json()

    # Taxable value is now ₹800, so 5% is ₹40 — not the ₹50 charged before.
    assert after["discount_total"] == 200.0
    assert after["tax_total"] == 40.0
    assert after["grand_total"] == 840.0


def test_gst_applies_to_the_service_charge(client, shop):
    """Bug 2. A service charge forms part of the value of supply, so GST is
    due on it. Ignoring it under-collects on every bill carrying one."""
    _settings(client, shop["headers"], default_tax_percent=5, default_service_charge_percent=10)
    order = _order(client, shop["headers"], shop["table"]["id"], shop["item"]["id"], 10)  # ₹1000
    bill = _bill(client, shop["headers"], order["session_id"])

    assert bill["subtotal"] == 1000.0
    assert bill["service_charge_total"] == 100.0
    # 5% of (1000 + 100), not 5% of 1000.
    assert bill["tax_total"] == 55.0
    assert bill["grand_total"] == 1155.0


def test_discount_and_service_charge_together(client, shop):
    """Both fixes interacting: charge on the discounted base, tax on both."""
    _settings(client, shop["headers"], default_tax_percent=5, default_service_charge_percent=10)
    order = _order(client, shop["headers"], shop["table"]["id"], shop["item"]["id"], 10)
    bill = _bill(client, shop["headers"], order["session_id"])

    resp = client.post(f"/api/v1/billing/{bill['id']}/discount",
                       json={"name": "Coupon", "amount": 200}, headers=shop["headers"])
    after = resp.json()

    # base 800; service charge 10% of 800 = 80; tax 5% of 880 = 44
    assert after["service_charge_total"] == 80.0
    assert after["tax_total"] == 44.0
    assert after["grand_total"] == 924.0


def test_discount_cannot_exceed_the_subtotal(client, shop):
    """A mistyped discount must not produce a negative taxable value."""
    _settings(client, shop["headers"], default_tax_percent=5, default_service_charge_percent=0)
    order = _order(client, shop["headers"], shop["table"]["id"], shop["item"]["id"], 5)  # ₹500
    bill = _bill(client, shop["headers"], order["session_id"])

    resp = client.post(f"/api/v1/billing/{bill['id']}/discount",
                       json={"name": "Oops", "amount": 5000}, headers=shop["headers"])
    after = resp.json()
    assert after["discount_total"] == 500.0
    assert after["tax_total"] == 0.0
    assert after["grand_total"] == 0.0


# ---------------------------------------------------------------------------
# CGST / SGST presentation
# ---------------------------------------------------------------------------

def test_intra_state_bill_shows_cgst_and_sgst_separately(client, shop):
    """A single combined 'GST 5%' line is not a compliant tax invoice, even
    though it adds up to the same money."""
    _settings(client, shop["headers"], default_tax_percent=5,
              default_service_charge_percent=0, tax_split_intra_state=True)
    order = _order(client, shop["headers"], shop["table"]["id"], shop["item"]["id"], 10)
    bill = _bill(client, shop["headers"], order["session_id"])

    names = sorted(t["name"] for t in bill["taxes"])
    assert names == ["CGST", "SGST"]
    assert all(t["percent"] == 2.5 for t in bill["taxes"])
    assert all(t["amount"] == 25.0 for t in bill["taxes"])
    assert bill["tax_total"] == 50.0


def test_split_can_be_turned_off_for_a_single_line(client, shop):
    _settings(client, shop["headers"], default_tax_percent=5,
              default_service_charge_percent=0, tax_split_intra_state=False)
    order = _order(client, shop["headers"], shop["table"]["id"], shop["item"]["id"], 10)
    bill = _bill(client, shop["headers"], order["session_id"])

    assert [t["name"] for t in bill["taxes"]] == ["GST"]
    assert bill["tax_total"] == 50.0


def test_gstin_is_validated(client, shop):
    bad = client.put("/api/v1/settings", json={"gstin": "NOT-A-GSTIN"}, headers=shop["headers"])
    assert bad.status_code == 422

    ok = client.put("/api/v1/settings", json={"gstin": "27AAPFU0939F1ZV"}, headers=shop["headers"])
    assert ok.status_code == 200, ok.text
    assert ok.json()["gstin"] == "27AAPFU0939F1ZV"

    cleared = client.put("/api/v1/settings", json={"gstin": ""}, headers=shop["headers"])
    assert cleared.status_code == 200
    assert cleared.json()["gstin"] is None


# ---------------------------------------------------------------------------
# charge bands
# ---------------------------------------------------------------------------

def _band(client, headers, **kw):
    payload = {"name": "Packing charge", "basis": "FLAT", "min_amount": 0, "value": 0, **kw}
    return client.post("/api/v1/charges/bands", json=payload, headers=headers)


def test_bands_are_selected_by_order_value(client, shop):
    h = shop["headers"]
    assert _band(client, h, min_amount=0, max_amount=200, value=20).status_code == 201
    assert _band(client, h, min_amount=200, max_amount=500, value=10).status_code == 201
    assert _band(client, h, min_amount=500, max_amount=None, value=0).status_code == 201

    def charge_at(amount):
        r = client.post("/api/v1/charges/preview", json={"amount": amount}, headers=h)
        assert r.status_code == 200, r.text
        return r.json()["charges_total"]

    assert charge_at(150) == 20.0
    assert charge_at(300) == 10.0
    assert charge_at(900) == 0.0


def test_band_boundaries_are_half_open(client, shop):
    """min is included, max is not — so ₹200 falls in the second band, and
    there is no value that lands in both or neither."""
    h = shop["headers"]
    _band(client, h, min_amount=0, max_amount=200, value=20)
    _band(client, h, min_amount=200, max_amount=500, value=10)

    def charge_at(amount):
        return client.post("/api/v1/charges/preview", json={"amount": amount},
                           headers=h).json()["charges_total"]

    assert charge_at(199.99) == 20.0
    assert charge_at(200) == 10.0
    assert charge_at(200.01) == 10.0


def test_overlapping_bands_are_rejected(client, shop):
    """Rejected at write time rather than resolved by a tie-break at bill
    time, because a tie-break rule is not predictable from the screen."""
    h = shop["headers"]
    assert _band(client, h, min_amount=0, max_amount=200, value=20).status_code == 201
    clash = _band(client, h, min_amount=100, max_amount=300, value=10)
    assert clash.status_code == 400
    assert "overlaps" in clash.text


def test_inverted_band_is_rejected(client, shop):
    bad = _band(client, shop["headers"], min_amount=500, max_amount=100, value=10)
    assert bad.status_code == 400


def test_gaps_are_reported_but_allowed(client, shop):
    h = shop["headers"]
    _band(client, h, min_amount=0, max_amount=100, value=20)
    _band(client, h, min_amount=200, max_amount=None, value=5)

    resp = client.get("/api/v1/charges/bands", headers=h)
    assert resp.status_code == 200
    gaps = resp.json()["gaps"]
    assert any(g["from_amount"] == 100.0 and g["to_amount"] == 200.0 for g in gaps)


def test_band_applies_to_a_real_bill_and_is_taxed(client, shop):
    h = shop["headers"]
    _settings(client, h, default_tax_percent=5, default_service_charge_percent=0)
    _band(client, h, name="Packing charge", min_amount=0, max_amount=None, value=30, is_taxable=True)

    order = _order(client, h, shop["table"]["id"], shop["item"]["id"], 10)  # ₹1000
    bill = _bill(client, h, order["session_id"])

    assert bill["service_charge_total"] == 30.0
    assert [c["name"] for c in bill["service_charges"]] == ["Packing charge"]
    # 5% of (1000 + 30)
    assert bill["tax_total"] == 51.5
    assert bill["grand_total"] == 1081.5


def test_non_taxable_band_is_excluded_from_tax(client, shop):
    h = shop["headers"]
    _settings(client, h, default_tax_percent=5, default_service_charge_percent=0)
    _band(client, h, name="Refundable deposit", min_amount=0, max_amount=None, value=100, is_taxable=False)

    order = _order(client, h, shop["table"]["id"], shop["item"]["id"], 10)
    bill = _bill(client, h, order["session_id"])

    assert bill["service_charge_total"] == 100.0
    assert bill["tax_total"] == 50.0          # 5% of 1000 only
    assert bill["grand_total"] == 1150.0


def test_percent_band_is_computed_on_the_discounted_base(client, shop):
    h = shop["headers"]
    _settings(client, h, default_tax_percent=0, default_service_charge_percent=0)
    _band(client, h, name="Service charge", basis="PERCENT", min_amount=0, max_amount=None, value=10)

    order = _order(client, h, shop["table"]["id"], shop["item"]["id"], 10)
    bill = _bill(client, h, order["session_id"])
    assert bill["service_charge_total"] == 100.0

    after = client.post(f"/api/v1/billing/{bill['id']}/discount",
                        json={"name": "Coupon", "amount": 200}, headers=h).json()
    assert after["service_charge_total"] == 80.0


def test_context_specific_band_beats_the_global_one(client, shop):
    h = shop["headers"]
    _band(client, h, name="Packing charge", min_amount=0, max_amount=None, value=10)
    _band(client, h, name="Packing charge", min_amount=0, max_amount=None, value=40,
          applies_to_context="DELIVERY")

    dine = client.post("/api/v1/charges/preview", json={"amount": 500, "context": "DINE_IN"},
                       headers=h).json()
    delivery = client.post("/api/v1/charges/preview", json={"amount": 500, "context": "DELIVERY"},
                           headers=h).json()
    assert dine["charges_total"] == 10.0
    assert delivery["charges_total"] == 40.0


def test_bands_are_owner_only(client, db_session, shop):
    other = register_and_login(client, db_session, business_name=f"Nosy {uuid.uuid4().hex[:6]}")
    resp = client.get("/api/v1/charges/bands", headers=other["headers"])
    assert resp.status_code == 200
    # Tenant isolation: a different business sees its own (empty) list.
    assert resp.json()["bands"] == []


def test_changing_a_band_does_not_alter_an_already_paid_bill(client, shop):
    """A paid bill is a record of what the guest actually paid. Re-deriving
    it from current configuration would rewrite history."""
    h = shop["headers"]
    _settings(client, h, default_tax_percent=5, default_service_charge_percent=0)
    _band(client, h, name="Packing charge", min_amount=0, max_amount=None, value=30)

    order = _order(client, h, shop["table"]["id"], shop["item"]["id"], 10)
    bill = _bill(client, h, order["session_id"])
    paid_total = bill["grand_total"]

    resp = client.post("/api/v1/payments/cash",
                       json={"bill_id": bill["id"], "amount": paid_total, "method": "CASH"}, headers=h)
    assert resp.status_code == 201, resp.text

    bands = client.get("/api/v1/charges/bands", headers=h).json()["bands"]
    band_id = [b for b in bands if b["name"] == "Packing charge"][0]["id"]
    client.put(f"/api/v1/charges/bands/{band_id}", json={"value": 999}, headers=h)

    again = client.get(f"/api/v1/billing/{bill['id']}", headers=h).json()
    assert again["grand_total"] == paid_total
    assert again["status"] == "PAID"
