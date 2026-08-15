"""Receipt content and rendering.

Two things are being defended.

First, that a printed bill carries everything an Indian tax invoice legally
must — GSTIN, FSSAI, a serial invoice number, CGST and SGST as separate
lines. These are asserted against the rendered output rather than the model,
because the failure that matters is a field existing in the database and not
reaching the paper.

Second, the ESC/POS byte stream. No thermal printer was available, so these
tests are the only verification that exists for it: they assert the exact
command bytes against the documented ESC/POS set. That is weaker than
printing a real bill and should not be mistaken for it — see
render_escpos.py's module docstring.
"""
import uuid

import pytest

from app.services.receipt import render_escpos as esc
from tests.helpers import create_category_and_item, create_table, register_and_login


def _order(client, headers, table_id, item_id, qty=2):
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
def settled(client, db_session):
    """A fully configured business with one paid bill."""
    owner = register_and_login(client, db_session, business_name=f"Receipt Biz {uuid.uuid4().hex[:6]}")
    client.put(
        "/api/v1/settings",
        json={
            "default_tax_percent": 5, "default_service_charge_percent": 0,
            "gstin": "27AAPFU0939F1ZV", "fssai_number": "11522998000123",
            "receipt_header_lines": "12 MG Road, Ahilyanagar\nPh 9822011234",
            "receipt_footer_text": "Thank you, visit again",
        },
        headers=owner["headers"],
    )
    _c, item = create_category_and_item(client, owner["headers"], price=100.0)
    table = create_table(client, owner["headers"], name=f"T{uuid.uuid4().hex[:4]}")
    order = _order(client, owner["headers"], table["id"], item["id"], qty=2)

    bill = client.post("/api/v1/billing/generate", json={"session_id": order["session_id"]},
                       headers=owner["headers"]).json()
    client.post("/api/v1/payments/cash",
                json={"bill_id": bill["id"], "amount": bill["grand_total"], "method": "CASH"},
                headers=owner["headers"])
    bill = client.get(f"/api/v1/billing/{bill['id']}", headers=owner["headers"]).json()
    return {"owner": owner, "headers": owner["headers"], "bill": bill, "item": item, "table": table}


def _text(client, settled, path_suffix="receipt", method="get", **params):
    url = f"/api/v1/billing/{settled['bill']['id']}/{path_suffix}"
    call = getattr(client, method)
    resp = call(url, params={"format": "text", **params}, headers=settled["headers"])
    assert resp.status_code == 200, resp.text
    return resp.text


# ---------------------------------------------------------------------------
# what a tax invoice must carry
# ---------------------------------------------------------------------------

def test_receipt_carries_every_legally_required_field(client, settled):
    body = _text(client, settled)
    assert "GSTIN: 27AAPFU0939F1ZV" in body
    assert "FSSAI: 11522998000123" in body
    assert settled["bill"]["invoice_number"] in body
    # Separate CGST and SGST lines, not one combined GST line.
    assert "CGST (2.5%)" in body
    assert "SGST (2.5%)" in body
    assert "GST (5%)" not in body


def test_receipt_shows_header_and_footer_lines(client, settled):
    body = _text(client, settled)
    assert "12 MG Road, Ahilyanagar" in body
    assert "Ph 9822011234" in body
    assert "Thank you, visit again" in body


def test_receipt_totals_match_the_bill(client, settled):
    body = _text(client, settled)
    bill = settled["bill"]
    assert f"{bill['subtotal']:.2f}" in body
    assert f"{bill['grand_total']:.2f}" in body
    assert "TOTAL" in body


def test_item_names_wrap_rather_than_truncate(client, db_session, settled):
    """A guest checking their bill has to recognise the dish. "Paneer Butter
    Mas" helps nobody."""
    long_name = "Hyderabadi Dum Biryani with Boneless Chicken and Raita"
    resp = client.post(
        "/api/v1/menu/items",
        json={"category_id": settled["item"]["category_id"], "name": long_name,
              "base_price": 450, "is_veg": False},
        headers=settled["headers"],
    )
    assert resp.status_code == 201, resp.text
    order = _order(client, settled["headers"], settled["table"]["id"], resp.json()["id"], qty=1)
    bill = client.post("/api/v1/billing/generate", json={"session_id": order["session_id"]},
                       headers=settled["headers"]).json()

    body = client.get(f"/api/v1/billing/{bill['id']}/receipt", params={"format": "text"},
                      headers=settled["headers"]).text
    # Every word survives somewhere, even though the line is wrapped.
    for word in ("Hyderabadi", "Boneless", "Raita"):
        assert word in body


# ---------------------------------------------------------------------------
# preview vs print
# ---------------------------------------------------------------------------

def test_preview_does_not_count_as_a_print(client, settled):
    """If it did, a cashier glancing at a bill on screen would turn the next
    genuine print into a 'duplicate'."""
    body = _text(client, settled)
    assert "PREVIEW - NOT A VALID BILL" in body

    after = client.get(f"/api/v1/billing/{settled['bill']['id']}", headers=settled["headers"]).json()
    assert after["print_count"] == 0


def test_first_print_is_clean_and_the_second_says_duplicate(client, settled):
    first = _text(client, settled, "print-receipt", method="post")
    assert "DUPLICATE COPY" not in first

    second = _text(client, settled, "print-receipt", method="post")
    assert "DUPLICATE COPY" in second

    after = client.get(f"/api/v1/billing/{settled['bill']['id']}", headers=settled["headers"]).json()
    assert after["print_count"] == 2


def test_cancelled_bill_is_marked_on_the_paper(client, settled):
    client.post(f"/api/v1/billing/{settled['bill']['id']}/void",
                json={"reason": "Guest walked out"}, headers=settled["headers"])
    body = _text(client, settled)
    assert "** CANCELLED **" in body
    assert "Guest walked out" in body


def test_unsettled_bill_does_not_present_its_internal_reference_as_an_invoice(client, settled):
    """An open bill has no invoice number, and printing the internal
    reference where a guest reads it as one would be worse than saying so."""
    order = _order(client, settled["headers"], settled["table"]["id"], settled["item"]["id"], qty=1)
    bill = client.post("/api/v1/billing/generate", json={"session_id": order["session_id"]},
                       headers=settled["headers"]).json()
    body = client.get(f"/api/v1/billing/{bill['id']}/receipt", params={"format": "text"},
                      headers=settled["headers"]).text
    assert "Bill (unsettled)" in body
    assert "Invoice " not in body


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def test_html_is_self_contained_and_sized_for_80mm(client, settled):
    """It renders in a hidden frame on a counter machine whose internet may
    well be down, so it cannot reference anything external."""
    resp = client.get(f"/api/v1/billing/{settled['bill']['id']}/receipt",
                      params={"format": "html"}, headers=settled["headers"])
    assert resp.status_code == 200
    body = resp.text
    assert "80mm" in body
    assert "<style>" in body
    assert "http://" not in body and "https://" not in body
    assert "<script" not in body


def test_html_escapes_item_names(client, settled):
    """A dish called 'Fish & Chips <spicy>' must not become markup."""
    resp = client.post(
        "/api/v1/menu/items",
        json={"category_id": settled["item"]["category_id"],
              "name": "Fish & Chips <spicy>", "base_price": 300, "is_veg": False},
        headers=settled["headers"],
    )
    order = _order(client, settled["headers"], settled["table"]["id"], resp.json()["id"], qty=1)
    bill = client.post("/api/v1/billing/generate", json={"session_id": order["session_id"]},
                       headers=settled["headers"]).json()
    body = client.get(f"/api/v1/billing/{bill['id']}/receipt", params={"format": "html"},
                      headers=settled["headers"]).text
    assert "&amp;" in body
    assert "<spicy>" not in body


# ---------------------------------------------------------------------------
# ESC/POS bytes — the only verification this renderer has
# ---------------------------------------------------------------------------

def test_escpos_starts_initialised_and_ends_cut(client, settled):
    resp = client.post(f"/api/v1/billing/{settled['bill']['id']}/print-receipt",
                       params={"format": "escpos"}, headers=settled["headers"])
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/octet-stream"
    raw = resp.content

    assert raw.startswith(esc.INIT), "printer must be reset to a known state first"
    assert raw.endswith(esc.FEED_AND_CUT), "receipt must end with a cut"


def test_escpos_command_bytes_match_the_documented_set():
    """Asserted literally, because nothing else verifies them. If a value
    here is wrong, a real printer is the only thing that would ever say so."""
    assert esc.INIT == b"\x1b@"
    assert esc.ALIGN_LEFT == b"\x1ba\x00"
    assert esc.ALIGN_CENTER == b"\x1ba\x01"
    assert esc.ALIGN_RIGHT == b"\x1ba\x02"
    assert esc.BOLD_ON == b"\x1bE\x01"
    assert esc.BOLD_OFF == b"\x1bE\x00"
    assert esc.SIZE_NORMAL == b"\x1d!\x00"
    assert esc.SIZE_DOUBLE_HEIGHT == b"\x1d!\x01"
    assert esc.FEED_AND_CUT == b"\x1dVB\x03"
    assert esc.DRAWER_KICK == b"\x1bp\x00\x19\xfa"


def test_escpos_restores_default_state_after_emphasis(client, settled):
    """Leaving a printer bold or double-height leaks into whatever prints
    next, which on a busy counter is the following guest's bill."""
    raw = client.post(f"/api/v1/billing/{settled['bill']['id']}/print-receipt",
                      params={"format": "escpos"}, headers=settled["headers"]).content
    assert raw.count(esc.BOLD_ON) == raw.count(esc.BOLD_OFF)
    assert raw.count(esc.SIZE_DOUBLE_HEIGHT) == raw.count(esc.SIZE_NORMAL)


def test_cash_drawer_opens_on_a_real_first_print_only(client, settled):
    """A preview or a reprint must not pop the till — someone re-reading a
    bill is not a reason to open the cash drawer."""
    preview = client.get(f"/api/v1/billing/{settled['bill']['id']}/receipt",
                         params={"format": "escpos"}, headers=settled["headers"]).content
    assert esc.DRAWER_KICK not in preview

    first = client.post(f"/api/v1/billing/{settled['bill']['id']}/print-receipt",
                        params={"format": "escpos"}, headers=settled["headers"]).content
    assert esc.DRAWER_KICK in first

    reprint = client.post(f"/api/v1/billing/{settled['bill']['id']}/print-receipt",
                          params={"format": "escpos"}, headers=settled["headers"]).content
    assert esc.DRAWER_KICK not in reprint


def test_escpos_survives_characters_outside_the_printer_codepage(client, settled):
    """A bill that prints 'Rs' where it wanted '₹' is still usable. One that
    raises stops the counter."""
    resp = client.post(
        "/api/v1/menu/items",
        json={"category_id": settled["item"]["category_id"],
              "name": "पनीर टिक्का", "base_price": 250, "is_veg": True},
        headers=settled["headers"],
    )
    order = _order(client, settled["headers"], settled["table"]["id"], resp.json()["id"], qty=1)
    bill = client.post("/api/v1/billing/generate", json={"session_id": order["session_id"]},
                       headers=settled["headers"]).json()

    raw = client.get(f"/api/v1/billing/{bill['id']}/receipt", params={"format": "escpos"},
                     headers=settled["headers"]).content
    assert raw.startswith(esc.INIT)
    assert raw.endswith(esc.FEED_AND_CUT)


# ---------------------------------------------------------------------------
# kitchen tickets
# ---------------------------------------------------------------------------

def test_kot_ticket_has_no_prices(client, settled):
    """Money on a kitchen ticket is noise, and worse, it invites the ticket
    being handed over as a bill."""
    order = _order(client, settled["headers"], settled["table"]["id"], settled["item"]["id"], qty=3)
    kots = client.get("/api/v1/kot", headers=settled["headers"]).json()
    kot = [k for k in kots if k["order_id"] == order["id"]][0]

    body = client.get(f"/api/v1/kot/{kot['id']}/ticket", params={"format": "text"},
                      headers=settled["headers"]).text
    assert kot["kot_number"] in body
    assert "TOTAL" not in body
    assert "GSTIN" not in body
    assert "100.00" not in body


def test_kot_ticket_splits_by_station(client, settled):
    """One order becomes a tandoor ticket and a Chinese ticket, so neither
    cook has to read past the other's items."""
    cat = settled["item"]["category_id"]
    tandoor = client.post("/api/v1/menu/items",
                          json={"category_id": cat, "name": "Tandoori Roti", "base_price": 30,
                                "is_veg": True, "kitchen_station": "TANDOOR"},
                          headers=settled["headers"]).json()
    chinese = client.post("/api/v1/menu/items",
                          json={"category_id": cat, "name": "Veg Noodles", "base_price": 180,
                                "is_veg": True, "kitchen_station": "CHINESE"},
                          headers=settled["headers"]).json()

    resp = client.post(
        "/api/v1/orders",
        json={"location_id": settled["table"]["id"], "source": "DINE_IN", "pricing_context": "DINE_IN",
              "items": [
                  {"menu_item_id": tandoor["id"], "variant_id": None, "quantity": 4, "option_ids": []},
                  {"menu_item_id": chinese["id"], "variant_id": None, "quantity": 1, "option_ids": []},
              ]},
        headers=settled["headers"],
    )
    order = resp.json()
    kots = client.get("/api/v1/kot", headers=settled["headers"]).json()
    kot = [k for k in kots if k["order_id"] == order["id"]][0]

    stations = client.get(f"/api/v1/kot/{kot['id']}/stations", headers=settled["headers"]).json()
    assert set(stations) == {"TANDOOR", "CHINESE"}

    tandoor_ticket = client.get(f"/api/v1/kot/{kot['id']}/ticket",
                                params={"format": "text", "station": "TANDOOR"},
                                headers=settled["headers"]).text
    assert "Tandoori Roti" in tandoor_ticket
    assert "Veg Noodles" not in tandoor_ticket

    chinese_ticket = client.get(f"/api/v1/kot/{kot['id']}/ticket",
                                params={"format": "text", "station": "CHINESE"},
                                headers=settled["headers"]).text
    assert "Veg Noodles" in chinese_ticket
    assert "Tandoori Roti" not in chinese_ticket


def test_unconfigured_stations_still_produce_one_ticket(client, settled):
    """A restaurant that never sets stations up must keep getting exactly one
    ticket per order."""
    order = _order(client, settled["headers"], settled["table"]["id"], settled["item"]["id"], qty=1)
    kots = client.get("/api/v1/kot", headers=settled["headers"]).json()
    kot = [k for k in kots if k["order_id"] == order["id"]][0]

    stations = client.get(f"/api/v1/kot/{kot['id']}/stations", headers=settled["headers"]).json()
    assert stations == [""]
