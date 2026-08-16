"""Turning bills and kitchen tickets into receipt documents.

Everything a printed tax invoice must legally carry is assembled here, once,
so it cannot be present on the browser copy and missing from the thermal
one. For an Indian restaurant that means: the business name and address, the
GSTIN, the FSSAI licence number, an invoice number from a consecutive
series, the CGST and SGST lines shown separately, and the date.
"""
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.billing import Bill
from app.models.business import Business, BusinessSettings
from app.models.kot import KOT
from app.models.location import Location
from app.models.menu import MenuItem
from app.models.order import Order, OrderItem
from app.services.receipt.document import Align, Emphasis, ReceiptDocument

DEFAULT_WIDTH = 48


def _money(amount) -> str:
    """Two decimals, no currency symbol.

    The symbol is left off deliberately: '₹' is outside cp437 and prints as
    a replacement character on most thermal printers, and a column of bare
    numbers under a heading reads fine on a till receipt anyway.
    """
    return f"{float(amount):.2f}"


def _local(dt: datetime, tz_name: str) -> str:
    try:
        tz = ZoneInfo(tz_name)
    except Exception:  # noqa: BLE001 - a bad timezone must not stop a bill printing
        tz = ZoneInfo("Asia/Kolkata")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz).strftime("%d/%m/%Y %H:%M")


def _header(doc: ReceiptDocument, business: Business, settings: BusinessSettings) -> None:
    doc.text(business.name, align=Align.CENTER, emphasis=Emphasis.BOLD_LARGE)

    for raw in (settings.receipt_header_lines or "").splitlines():
        if raw.strip():
            doc.text(raw.strip(), align=Align.CENTER)

    if settings.gstin:
        doc.text(f"GSTIN: {settings.gstin}", align=Align.CENTER)
    # Required on the bill of any licensed food business in India.
    if settings.fssai_number:
        doc.text(f"FSSAI: {settings.fssai_number}", align=Align.CENTER)


def build_bill_receipt(
    db: Session,
    business_id: uuid.UUID,
    bill: Bill,
    *,
    is_duplicate: bool = False,
    is_preview: bool = False,
    width: int = DEFAULT_WIDTH,
) -> ReceiptDocument:
    business = db.get(Business, business_id)
    settings = db.query(BusinessSettings).filter(
        BusinessSettings.business_id == business_id
    ).first()
    tz_name = settings.timezone if settings else "Asia/Kolkata"

    doc = ReceiptDocument(
        width=width,
        # Only a real, settled, non-duplicate print should pop the till. A
        # preview or a reprint must not — someone re-reading a bill is not a
        # reason to open the cash drawer.
        open_cash_drawer=not is_preview and not is_duplicate and bill.invoice_number is not None,
        title=bill.invoice_number or bill.bill_number,
    )

    _header(doc, business, settings)
    doc.divider()

    # A copy that is not the original says so at the top, where it cannot be
    # missed, rather than in small print at the bottom.
    if is_duplicate:
        doc.text("DUPLICATE COPY", align=Align.CENTER, emphasis=Emphasis.BOLD)
        doc.divider()
    if is_preview:
        doc.text("PREVIEW - NOT A VALID BILL", align=Align.CENTER, emphasis=Emphasis.BOLD)
        doc.divider()
    if bill.status.value == "CANCELLED":
        doc.text("** CANCELLED **", align=Align.CENTER, emphasis=Emphasis.BOLD)
        if bill.void_reason:
            doc.text(bill.void_reason, align=Align.CENTER)
        doc.divider()
    if bill.is_nc:
        doc.text("** NO CHARGE **", align=Align.CENTER, emphasis=Emphasis.BOLD)
        if bill.nc_reason:
            doc.text(bill.nc_reason, align=Align.CENTER)
        doc.divider()

    if bill.invoice_number:
        doc.pair("Invoice", bill.invoice_number)
    elif bill.is_nc:
        # An NC bill never gets a tax invoice number — nothing was supplied
        # for consideration, so there is no taxable supply to invoice. Saying
        # so beats printing the internal reference under an "Invoice" label
        # that would misrepresent what this document is.
        doc.pair("No-charge bill", bill.bill_number)
    else:
        # An unsettled bill has no invoice number yet, and saying so is
        # better than printing the internal reference where a guest would
        # read it as one.
        doc.pair("Bill (unsettled)", bill.bill_number)

    doc.pair("Date", _local(bill.finalised_at or bill.created_at, tz_name))

    if bill.location_id:
        location = db.get(Location, bill.location_id)
        if location is not None:
            doc.pair("Table", location.name)

    doc.divider()
    doc.pair("Item", "Amount", emphasis=Emphasis.BOLD)
    doc.divider()

    for item in bill.items:
        # A struck line is not the guest's business — it contributes nothing
        # to the total, so printing it only invites an argument about a dish
        # they are not being charged for. It stays on the bill record and in
        # the audit log, where someone reviewing the shift can find it.
        if item.is_voided:
            continue
        qty = int(float(item.quantity)) if float(item.quantity).is_integer() else float(item.quantity)
        # A comped line does print, unlike a voided one. The guest was served
        # the dish and the restaurant wants credit for giving it — a gesture
        # nobody sees is not a gesture. The rate stays visible so the value of
        # what was given is on the paper; only the amount reads NC.
        doc.item(
            item.item_name_snapshot,
            quantity=str(qty),
            rate=_money(item.unit_price),
            amount="NC" if item.is_comped else _money(item.line_total),
        )

    doc.divider()
    doc.pair("Subtotal", _money(bill.subtotal))

    for discount in bill.discounts:
        label = discount.name or "Discount"
        doc.pair(f"{label} (-)", _money(discount.amount))

    for charge in bill.service_charges:
        label = charge.name
        if charge.percent is not None:
            label = f"{label} ({float(charge.percent):g}%)"
        doc.pair(label, _money(charge.amount))

    for tax in bill.taxes:
        doc.pair(f"{tax.name} ({float(tax.percent):g}%)", _money(tax.amount))

    if float(bill.round_off or 0) != 0:
        doc.pair("Round off", _money(bill.round_off))

    doc.divider()
    doc.pair("TOTAL", _money(bill.grand_total), emphasis=Emphasis.BOLD_LARGE)

    if float(bill.amount_refunded or 0) > 0:
        doc.pair("Refunded", _money(bill.amount_refunded))

    doc.divider()

    footer = (settings.receipt_footer_text or "").strip() if settings else ""
    if footer:
        doc.spacer()
        for raw in footer.splitlines():
            doc.text(raw.strip(), align=Align.CENTER)

    doc.spacer()
    return doc


def build_kot_ticket(
    db: Session,
    business_id: uuid.UUID,
    kot: KOT,
    *,
    station: str | None = None,
    width: int = DEFAULT_WIDTH,
) -> ReceiptDocument:
    """A kitchen ticket.

    Deliberately spare: no prices, no tax, no business address. A cook needs
    the table, the items, and anything unusual about them, in the largest
    type that fits. Money on a kitchen ticket is noise, and worse, it invites
    the ticket being used as a bill.

    When `station` is given, only that station's items appear — which is how
    one order becomes a tandoor ticket and a Chinese ticket without the cook
    at either having to read past the other's items.
    """
    doc = ReceiptDocument(width=width, open_cash_drawer=False, title=kot.kot_number)
    settings = db.query(BusinessSettings).filter(
        BusinessSettings.business_id == business_id
    ).first()
    tz_name = settings.timezone if settings else "Asia/Kolkata"

    heading = station or "KITCHEN"
    doc.text(heading.upper(), align=Align.CENTER, emphasis=Emphasis.BOLD_LARGE)
    doc.divider()

    doc.pair("KOT", kot.kot_number, emphasis=Emphasis.BOLD)
    doc.pair("Time", _local(kot.created_at, tz_name))

    if kot.location_id:
        location = db.get(Location, kot.location_id)
        if location is not None:
            doc.text(f"TABLE {location.name}", align=Align.CENTER, emphasis=Emphasis.BOLD_LARGE)

    order = db.get(Order, kot.order_id)
    if order is not None and order.is_additional:
        # The single most useful thing on an add-on ticket: this is extra
        # food for a table that is already eating, not a new order.
        doc.text("** ADDITIONAL ORDER **", align=Align.CENTER, emphasis=Emphasis.BOLD)

    doc.divider()

    items = _kot_items_for_station(db, business_id, kot, station)
    for item in items:
        doc.item(item.item_name_snapshot, quantity=str(item.quantity), rate="", amount="")
        if item.options_summary:
            doc.sub_text(item.options_summary)

    if kot.special_instructions:
        doc.divider()
        doc.text("NOTE", emphasis=Emphasis.BOLD)
        doc.text(kot.special_instructions)

    doc.spacer()
    return doc


def _kot_items_for_station(db: Session, business_id: uuid.UUID, kot: KOT, station: str | None):
    if station is None:
        return list(kot.items)

    # KOTItem records a name snapshot rather than a menu item id, so the
    # station is resolved through the order item it came from. Snapshots
    # exist so a later menu edit cannot rewrite a printed ticket, and that is
    # worth the extra hop here.
    order_item_ids = [i.order_item_id for i in kot.items]
    stations = dict(
        db.query(OrderItem.id, MenuItem.kitchen_station)
        .join(MenuItem, MenuItem.id == OrderItem.menu_item_id)
        .filter(OrderItem.id.in_(order_item_ids))
        .all()
    )
    return [i for i in kot.items if (stations.get(i.order_item_id) or "") == station]


def stations_for_kot(db: Session, business_id: uuid.UUID, kot: KOT) -> list[str]:
    """Which stations this ticket needs to be printed to.

    An item with no station configured lands in the empty-string group, which
    the caller renders as the default kitchen ticket — so a restaurant that
    never sets stations up keeps getting exactly one ticket per order.
    """
    order_item_ids = [i.order_item_id for i in kot.items]
    if not order_item_ids:
        return []
    rows = (
        db.query(MenuItem.kitchen_station)
        .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
        .filter(OrderItem.id.in_(order_item_ids))
        .distinct()
        .all()
    )
    return sorted({(r[0] or "") for r in rows})


def build_shift_report(
    db: Session,
    business_id: uuid.UUID,
    report: dict,
    *,
    width: int = DEFAULT_WIDTH,
) -> ReceiptDocument:
    """The Z-report as printable paper.

    Reuses the same document the bills use, which is the point of having
    built one: a report that prints on the counter's existing roll, in the
    same shape, with no second layout system to maintain.

    The variance is the line an owner actually reads, so it is the only thing
    emphasised.
    """
    business = db.get(Business, business_id)
    settings = db.query(BusinessSettings).filter(
        BusinessSettings.business_id == business_id
    ).first()
    tz_name = settings.timezone if settings else "Asia/Kolkata"

    doc = ReceiptDocument(width=width, open_cash_drawer=False, title="Shift report")

    doc.text(business.name, align=Align.CENTER, emphasis=Emphasis.BOLD_LARGE)
    doc.text("SHIFT REPORT", align=Align.CENTER, emphasis=Emphasis.BOLD)
    doc.divider()

    if report.get("opened_by"):
        doc.pair("Cashier", report["opened_by"])
    doc.pair("Opened", _local(report["opened_at"], tz_name))
    if report.get("closed_at"):
        doc.pair("Closed", _local(report["closed_at"], tz_name))

    doc.divider()
    doc.text("TAKINGS", emphasis=Emphasis.BOLD)
    for line in report["payments"]:
        doc.pair(f"{line['method']} x{line['count']}", _money(line["amount"]))
    doc.pair("Gross", _money(report["gross_takings"]), emphasis=Emphasis.BOLD)

    if report["refunds_count"]:
        doc.pair(f"Refunds x{report['refunds_count']}", f"-{_money(report['refunds_total'])}")

    doc.divider()
    doc.text("CASH DRAWER", emphasis=Emphasis.BOLD)
    doc.pair("Opening float", _money(report["opening_float"]))
    doc.pair("Cash taken", _money(report["cash_taken"]))
    if report["cash_returned"]:
        doc.pair("Cash returned", f"-{_money(report['cash_returned'])}")

    # Null while the drawer is open under blind counting. Printing a report
    # in that state must not be a way around the control.
    if report["expected_cash"] is not None:
        doc.pair("Expected", _money(report["expected_cash"]))
    else:
        doc.pair("Expected", "(counted at close)")

    if report["declared_cash"] is not None:
        doc.pair("Counted", _money(report["declared_cash"]))
    if report["variance"] is not None:
        variance = float(report["variance"])
        label = "OVER" if variance > 0 else ("SHORT" if variance < 0 else "BALANCED")
        doc.pair(f"Variance ({label})", _money(variance), emphasis=Emphasis.BOLD_LARGE)

    doc.divider()
    doc.text("EXCEPTIONS", emphasis=Emphasis.BOLD)
    # A drawer that balances perfectly while ten bills were voided is not a
    # drawer that balanced, so these sit next to the variance rather than
    # somewhere an owner has to go looking for them.
    doc.pair("Bills settled", str(report["bills_settled"]))
    doc.pair("Bills voided", str(report["bills_voided"]))
    doc.pair("Discounts given", _money(report["discounts_total"]))

    if report.get("notes"):
        doc.divider()
        doc.text("NOTE", emphasis=Emphasis.BOLD)
        doc.text(report["notes"])

    doc.spacer()
    doc.text("Cashier signature: ____________________")
    doc.spacer()
    return doc
