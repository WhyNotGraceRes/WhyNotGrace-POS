import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core import toggles
from app.core.permissions import ROLE_OPERATIONAL
from app.core.ws_manager import manager as ws_manager
from app.models.billing import Bill, BillDiscount, BillItem, BillServiceCharge, BillTax
from app.models.business import BusinessSettings
from app.models.enums import BillStatus, ChargeBasis, LocationStatus, OrderStatus, PricingContext
from app.models.location import Location
from app.models.order import Order, OrderSession
from app.services import charge_service, invoice_service
from app.utils.numbering import generate_number


def _bill_query(db: Session, business_id: uuid.UUID):
    return (
        db.query(Bill)
        .populate_existing()
        .options(
            joinedload(Bill.items), joinedload(Bill.taxes), joinedload(Bill.discounts),
            joinedload(Bill.service_charges), joinedload(Bill.payments),
        )
        .filter(Bill.business_id == business_id)
    )


def get_bill_or_404(db: Session, business_id: uuid.UUID, bill_id: uuid.UUID) -> Bill:
    bill = _bill_query(db, business_id).filter(Bill.id == bill_id).first()
    if bill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return bill


def list_unbilled_orders(db: Session, business_id: uuid.UUID) -> list[Order]:
    """Orders that still need billing attention right now.

    There is no "list all bills" endpoint by design (see billing.py's
    module docstring) — this answers a narrower, safer question: which
    orders have no money settled against them yet.

    `OrderSession.is_closed` cannot answer this — it is written nowhere in
    the codebase (see docs/billing-counter-plan.md, "A settled table can be
    billed again"), so a table's very first session is reused forever and
    naively grouping "all orders for this session" would resurface a whole
    table's history on every visit. Instead this looks at each session's
    most recent bill: no bill, or one still OPEN/PARTIALLY_PAID, means the
    whole session needs billing; a PAID/CANCELLED bill means only whatever
    was ordered *after* that bill last changed (a genuine new round at a
    table that already settled) still needs it — everything settled on that
    bill itself is correctly left out.
    """
    orders = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.customer))
        .filter(Order.business_id == business_id, Order.status != OrderStatus.CANCELLED)
        .order_by(Order.created_at.desc())
        .all()
    )
    if not orders:
        return []

    session_ids = {o.session_id for o in orders}
    bills = (
        db.query(Bill)
        .filter(Bill.business_id == business_id, Bill.session_id.in_(session_ids))
        .order_by(Bill.created_at.desc())
        .all()
    )
    latest_bill_by_session: dict[uuid.UUID, Bill] = {}
    for bill in bills:
        latest_bill_by_session.setdefault(bill.session_id, bill)

    result = []
    for order in orders:
        bill = latest_bill_by_session.get(order.session_id)
        if bill is None or bill.status in (BillStatus.OPEN, BillStatus.PARTIALLY_PAID):
            result.append(order)
        elif order.created_at > bill.updated_at:
            result.append(order)
    return result


def _recompute_totals(db: Session, business_id: uuid.UUID, bill: Bill) -> None:
    """Recomputes every derived total on the bill.

    The order of operations is the whole point here, and it was previously
    wrong in two ways that each showed up as real money:

    1. Tax was charged on the raw subtotal, so a discount reduced what the
       guest paid but not what they were taxed on. Under GST the taxable
       value is the value *after* a discount shown on the invoice, so every
       discounted bill over-charged the guest and over-remitted to the
       government.
    2. Tax ignored service and other charges entirely. A service, packing or
       delivery charge on a restaurant bill forms part of the value of
       supply and attracts GST, so every bill carrying one under-collected.

    The correct sequence:

        taxable base  = subtotal - discounts
        charges       = percent of that base, or a flat amount
        taxable value = taxable base + charges that are taxable
        tax           = taxable value x rate
        grand total   = taxable base + all charges + tax

    Percentage charges are computed on the discounted base for the same
    reason as the tax: a 10% service charge on food the guest was never
    billed for is a charge on nothing.
    """
    # Voided and complimentary lines both stop contributing money, for
    # different reasons: a void was never supplied, a comp was supplied and
    # given away. Neither carries consideration, so neither belongs in the
    # taxable value.
    subtotal = sum(float(i.line_total) for i in bill.items if i.is_chargeable)
    discount_total = sum(float(d.amount) for d in bill.discounts)

    # A discount can never take the bill below zero. A data-entry slip
    # (₹5000 off a ₹500 bill) must not produce a negative taxable value and
    # a tax credit the restaurant never intended to give.
    discount_total = min(discount_total, subtotal)
    taxable_base = subtotal - discount_total

    charges_total = 0.0
    taxable_charges = 0.0
    for sc in bill.service_charges:
        if sc.percent is not None:
            sc.amount = round(taxable_base * float(sc.percent) / 100, 2)
        # A flat charge keeps the amount it was created with — there is no
        # percentage to recompute it from.
        amount = float(sc.amount)
        charges_total += amount
        if sc.is_taxable:
            taxable_charges += amount

    taxable_value = taxable_base + taxable_charges

    tax_total = 0.0
    for tax in bill.taxes:
        tax.amount = round(taxable_value * float(tax.percent) / 100, 2)
        tax_total += tax.amount

    payable = round(taxable_base + charges_total + tax_total, 2)

    # Round-off is applied last, after tax, and never folded into the taxable
    # value. Rounding before tax would change the amount GST is computed on,
    # which is not ours to adjust — the round-off is a convenience for handling
    # cash, not a change to the value of supply.
    round_off = 0.0
    if toggles.is_enabled(db, business_id, toggles.ROUND_OFF_TOTAL):
        rounded = round(payable)
        round_off = round(rounded - payable, 2)
        payable = float(rounded)

    bill.subtotal = round(subtotal, 2)
    bill.tax_total = round(tax_total, 2)
    bill.service_charge_total = round(charges_total, 2)
    bill.discount_total = round(discount_total, 2)
    bill.round_off = round_off
    bill.grand_total = payable

    if bill.status not in (BillStatus.PAID, BillStatus.CANCELLED):
        if bill.amount_paid <= 0:
            bill.status = BillStatus.OPEN
        elif bill.amount_paid < bill.grand_total:
            bill.status = BillStatus.PARTIALLY_PAID
        else:
            bill.status = BillStatus.PAID


def _tax_components(settings_row: BusinessSettings) -> list[tuple[str, float]]:
    """Splits the configured rate into the lines that appear on the invoice.

    An intra-state restaurant supply — the guest eating where the restaurant
    is, which is nearly every bill — must show CGST and SGST separately at
    half the rate each. A single "GST 5%" line is not a compliant tax
    invoice, even though it adds up to the same money.
    """
    rate = float(settings_row.default_tax_percent)
    label = settings_row.tax_label or "GST"
    if not settings_row.tax_split_intra_state:
        return [(label, rate)]
    half = round(rate / 2, 2)
    return [(f"C{label}", half), (f"S{label}", half)]


def _charge_context(db: Session, session: OrderSession) -> PricingContext | None:
    """Which fulfilment context this session's bill is for.

    Taken from the session's orders rather than the session itself, since
    pricing_context is what actually drove the prices on the bill. A session
    with no surviving orders has no context, in which case only bands that
    apply to every context can match.
    """
    order = (
        db.query(Order)
        .filter(Order.session_id == session.id, Order.status != OrderStatus.CANCELLED)
        .order_by(Order.created_at)
        .first()
    )
    return order.pricing_context if order else None


def _apply_charge_bands(db: Session, business_id: uuid.UUID, bill: Bill, session: OrderSession) -> bool:
    """Adds one charge line per owner-defined ladder that matches this bill.

    The value a band is matched against is the discounted subtotal — the
    same base the charge is computed on — so "free delivery above ₹500"
    means ₹500 of food actually paid for, not ₹500 before a coupon.

    Returns whether anything was applied, so the caller knows if it still
    needs to fall back to the flat default.
    """
    subtotal = sum(float(i.line_total) for i in bill.items)
    discount_total = min(sum(float(d.amount) for d in bill.discounts), subtotal)
    base = subtotal - discount_total

    context = _charge_context(db, session)
    bands = charge_service.select_bands_for(db, business_id, base=base, context=context)
    for band in bands:
        if band.basis == ChargeBasis.PERCENT:
            db.add(
                BillServiceCharge(
                    business_id=business_id, bill_id=bill.id, name=band.name,
                    percent=float(band.value), amount=0, is_taxable=band.is_taxable,
                )
            )
        else:
            db.add(
                BillServiceCharge(
                    business_id=business_id, bill_id=bill.id, name=band.name,
                    percent=None, amount=float(band.value), is_taxable=band.is_taxable,
                )
            )
    return bool(bands)


def generate_or_refresh_bill(db: Session, business_id: uuid.UUID, payload) -> Bill:
    """Create a bill for an order session, or (if one already exists and
    is still open) sync in any newly-added order items — this is how
    additional orders get reflected on the same bill.
    """
    session = db.query(OrderSession).filter(
        OrderSession.id == payload.session_id, OrderSession.business_id == business_id
    ).first()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order session not found")

    bill = (
        _bill_query(db, business_id)
        .filter(Bill.session_id == session.id, Bill.status.in_([BillStatus.OPEN, BillStatus.PARTIALLY_PAID]))
        .first()
    )
    if bill is None:
        bill = Bill(
            business_id=business_id, session_id=session.id, location_id=session.location_id,
            bill_number=generate_number("BILL"), status=BillStatus.OPEN,
        )
        db.add(bill)
        db.flush()

    already_billed_item_ids = {bi.order_item_id for bi in bill.items}
    orders = db.query(Order).filter(
        Order.session_id == session.id, Order.status != OrderStatus.CANCELLED
    ).all()
    for order in orders:
        for item in order.items:
            if item.id in already_billed_item_ids:
                continue
            db.add(
                BillItem(
                    business_id=business_id, bill_id=bill.id, order_item_id=item.id,
                    item_name_snapshot=item.item_name_snapshot, quantity=item.quantity,
                    unit_price=item.unit_price, line_total=item.line_total,
                )
            )
    db.flush()

    settings_row = db.query(BusinessSettings).filter(BusinessSettings.business_id == business_id).first()

    if not bill.taxes:
        if payload.taxes:
            for t in payload.taxes:
                db.add(BillTax(business_id=business_id, bill_id=bill.id, name=t.name, percent=t.percent, amount=0))
        elif payload.use_default_tax and settings_row and settings_row.default_tax_percent > 0:
            for name, percent in _tax_components(settings_row):
                db.add(
                    BillTax(business_id=business_id, bill_id=bill.id, name=name, percent=percent, amount=0)
                )

    if not bill.service_charges:
        if payload.service_charges:
            for sc in payload.service_charges:
                db.add(
                    BillServiceCharge(business_id=business_id, bill_id=bill.id, name=sc.name, percent=sc.percent, amount=0)
                )
        else:
            # Owner-defined bands first — they are the specific, deliberate
            # configuration. The flat default_service_charge_percent is the
            # fallback for a business that has not set any up, so existing
            # deployments keep behaving exactly as before.
            applied_any = False
            if payload.use_default_service_charge:
                applied_any = _apply_charge_bands(db, business_id, bill, session)
            if not applied_any and payload.use_default_service_charge and settings_row and settings_row.default_service_charge_percent > 0:
                db.add(
                    BillServiceCharge(
                        business_id=business_id, bill_id=bill.id, name="Service Charge",
                        percent=settings_row.default_service_charge_percent, amount=0, is_taxable=True,
                    )
                )
    db.flush()

    bill = get_bill_or_404(db, business_id, bill.id)
    _recompute_totals(db, business_id, bill)
    db.flush()
    return bill


def apply_discount(db: Session, business_id: uuid.UUID, bill_id: uuid.UUID, payload, staff_id: uuid.UUID) -> Bill:
    bill = get_bill_or_404(db, business_id, bill_id)
    if bill.status in (BillStatus.PAID, BillStatus.CANCELLED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify a closed bill")

    if payload.amount is not None:
        amount = float(payload.amount)
    elif payload.percent is not None:
        amount = round(float(bill.subtotal) * float(payload.percent) / 100, 2)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide either percent or amount")

    db.add(
        BillDiscount(
            business_id=business_id, bill_id=bill.id, name=payload.name, percent=payload.percent,
            amount=amount, reason=payload.reason, applied_by_staff_id=staff_id,
        )
    )
    db.flush()
    bill = get_bill_or_404(db, business_id, bill.id)
    _recompute_totals(db, business_id, bill)
    db.flush()
    return bill


def record_payment_applied(db: Session, business_id: uuid.UUID, bill_id: uuid.UUID, amount: float) -> Bill:
    bill = get_bill_or_404(db, business_id, bill_id)
    was_paid_before = bill.status == BillStatus.PAID
    bill.amount_paid = round(float(bill.amount_paid) + amount, 2)
    _recompute_totals(db, business_id, bill)
    db.flush()

    if bill.status == BillStatus.PAID and bill.location_id:
        location = db.get(Location, bill.location_id)
        if location is not None:
            location.status = LocationStatus.PAID
            db.flush()

    if bill.status == BillStatus.PAID and not was_paid_before:
        from app.services import kot_service

        # Settlement is the moment the bill becomes a tax invoice, so this is
        # where its number is allocated — see invoice_service for why not at
        # creation. Guarded by `not was_paid_before` so a second payment on an
        # already-settled bill can never allocate a second number.
        finalise(db, business_id, bill)

        kot_service.release_held_kots_for_session(db, business_id, bill.session_id)
        _accrue_loyalty_if_enabled(db, business_id, bill)

    return bill


def finalise(db: Session, business_id: uuid.UUID, bill: Bill) -> Bill:
    """Turns a settled bill into a numbered tax invoice.

    Idempotent: a bill that already carries a number keeps it. Anything that
    re-runs this — a retried request, a webhook arriving twice — must not
    consume a second serial.
    """
    if bill.invoice_number is not None:
        return bill

    number, series, fy, sequence = invoice_service.allocate(db, business_id)
    bill.invoice_number = number
    bill.invoice_series = series
    bill.invoice_financial_year = fy
    bill.invoice_sequence = sequence
    bill.finalised_at = datetime.now(timezone.utc)
    db.flush()
    return bill


def void_bill(db: Session, business_id: uuid.UUID, bill_id: uuid.UUID, *, reason: str | None, user) -> Bill:
    """Cancels a bill without deleting it.

    A voided invoice keeps its number and stays in the series. Removing it
    would create exactly the gap the numbering rules forbid, and would erase
    the record of the cancellation — which is the thing an owner most wants
    to be able to look at.
    """
    bill = get_bill_or_404(db, business_id, bill_id)
    if bill.status == BillStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bill is already cancelled")

    if toggles.is_enabled(db, business_id, toggles.VOID_REQUIRES_MANAGER):
        if user.role not in ROLE_OPERATIONAL:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only a manager or owner can void a bill",
            )

    if toggles.is_enabled(db, business_id, toggles.VOID_REQUIRES_REASON):
        if not reason or not reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A reason is required to void a bill",
            )

    bill.status = BillStatus.CANCELLED
    bill.voided_at = datetime.now(timezone.utc)
    bill.void_reason = (reason or "").strip() or None
    bill.voided_by_user_id = user.id
    db.flush()

    # Free the table. A cancelled bill should not leave the floor plan
    # showing a location as still owing money.
    if bill.location_id:
        location = db.get(Location, bill.location_id)
        if location is not None:
            location.status = LocationStatus.AVAILABLE
            db.flush()

    ws_manager.notify(business_id, "billing", "tables", "orders")
    return bill


def void_bill_item(
    db: Session, business_id: uuid.UUID, bill_id: uuid.UUID, item_id: uuid.UUID, *, reason: str | None, user
) -> Bill:
    """Strikes one line off a bill and recomputes the totals.

    Voiding a whole bill is a different act with a different record — this is
    the everyday one: a dish sent back, rung up twice, or ordered by mistake.
    The line is marked rather than deleted (see BillItem.voided_at) and the
    bill's totals, tax and charges all fall out of the existing recompute, so
    a struck line reduces the taxable value the same way it would have raised
    it.

    The same two toggles that guard a whole-bill void guard this one. A
    counter that requires a manager to void a bill plainly does not intend a
    cashier to be able to empty that bill one line at a time.
    """
    bill = get_bill_or_404(db, business_id, bill_id)
    if bill.status in (BillStatus.PAID, BillStatus.CANCELLED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify a closed bill")

    item = next((i for i in bill.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill item not found")
    if item.is_voided:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item is already voided")

    if toggles.is_enabled(db, business_id, toggles.VOID_REQUIRES_MANAGER):
        if user.role not in ROLE_OPERATIONAL:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only a manager or owner can void an item",
            )

    if toggles.is_enabled(db, business_id, toggles.VOID_REQUIRES_REASON):
        if not reason or not reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A reason is required to void an item",
            )

    item.voided_at = datetime.now(timezone.utc)
    item.void_reason = (reason or "").strip() or None
    item.voided_by_user_id = user.id
    db.flush()

    bill = get_bill_or_404(db, business_id, bill_id)
    _recompute_totals(db, business_id, bill)
    db.flush()
    return bill


def _require_comp_authority(db: Session, business_id: uuid.UUID, *, reason: str | None, user, what: str) -> None:
    """The two toggles that guard giving food away, in one place.

    Separate from the void toggles on purpose: a restaurant may well want a
    cashier to be able to strike a dish that never left the kitchen, while
    still insisting a manager signs off anything given away.
    """
    if toggles.is_enabled(db, business_id, toggles.COMP_REQUIRES_MANAGER):
        if user.role not in ROLE_OPERATIONAL:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Only a manager or owner can {what}",
            )

    if toggles.is_enabled(db, business_id, toggles.COMP_REQUIRES_REASON):
        if not reason or not reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A reason is required to {what}",
            )


def comp_bill_item(
    db: Session, business_id: uuid.UUID, bill_id: uuid.UUID, item_id: uuid.UUID, *, reason: str | None, user
) -> Bill:
    """Gives one line away without removing it from the bill.

    The line keeps its price and still prints, marked NC — a guest who was
    given a dessert should see the dessert and see that it was free. It simply
    stops contributing to the subtotal, so tax and percentage charges fall
    with it.
    """
    bill = get_bill_or_404(db, business_id, bill_id)
    if bill.status in (BillStatus.PAID, BillStatus.CANCELLED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify a closed bill")

    item = next((i for i in bill.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill item not found")
    if item.is_voided:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That line is voided — a dish that was never supplied cannot be given away",
        )
    if item.is_comped:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item is already complimentary")

    _require_comp_authority(db, business_id, reason=reason, user=user, what="give an item free")

    item.comped_at = datetime.now(timezone.utc)
    item.comp_reason = (reason or "").strip() or None
    item.comped_by_user_id = user.id
    db.flush()

    bill = get_bill_or_404(db, business_id, bill_id)
    _recompute_totals(db, business_id, bill)
    db.flush()
    return bill


def uncomp_bill_item(
    db: Session, business_id: uuid.UUID, bill_id: uuid.UUID, item_id: uuid.UUID, *, user
) -> Bill:
    """Puts a comped line back on the bill.

    Reversible where a void is not, because the two claims are different. A
    void asserts a fact about the kitchen — that the dish was never supplied —
    and unsaying it would be rewriting history. A comp is only a pricing
    decision, and the manager who made it may reasonably change their mind
    before the guest pays.
    """
    bill = get_bill_or_404(db, business_id, bill_id)
    if bill.status in (BillStatus.PAID, BillStatus.CANCELLED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify a closed bill")
    if bill.is_nc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is a no-charge bill — remove the no-charge mark first",
        )

    item = next((i for i in bill.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill item not found")
    if not item.is_comped:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item is not complimentary")

    _require_comp_authority(db, business_id, reason="uncomp", user=user, what="charge for an item again")

    item.comped_at = None
    item.comp_reason = None
    item.comped_by_user_id = None
    db.flush()

    bill = get_bill_or_404(db, business_id, bill_id)
    _recompute_totals(db, business_id, bill)
    db.flush()
    return bill


def mark_bill_nc(db: Session, business_id: uuid.UUID, bill_id: uuid.UUID, *, reason: str | None, user) -> Bill:
    """Marks a whole bill no-charge: a staff meal, or a table the owner
    decided not to bill.

    Every line is comped, so the bill lands at zero through the ordinary
    recompute rather than by writing a zero over the top of it — the lines,
    their prices, and the tax that would have applied all stay legible.

    The bill then settles without a payment, because there is no money to
    record and inventing a zero-rupee CASH payment would put a fictional row
    into the shift's takings and the Z-report.

    It does NOT allocate a tax invoice number. The invoice series is the GST
    serial (see invoice_service), and food given away for no consideration is
    not a taxable supply — burning a serial on it would put a zero-value
    invoice into the return. The internal bill_number still identifies it.
    """
    bill = get_bill_or_404(db, business_id, bill_id)
    if bill.status == BillStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bill is cancelled")
    if bill.is_nc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bill is already no-charge")
    if float(bill.amount_paid) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Money has already been taken on this bill — refund it before marking no-charge",
        )

    _require_comp_authority(db, business_id, reason=reason, user=user, what="mark a bill no-charge")

    now = datetime.now(timezone.utc)
    bill.nc_at = now
    bill.nc_reason = (reason or "").strip() or None
    bill.nc_by_user_id = user.id

    for item in bill.items:
        # A voided line stays voided. It was never supplied, so it is not
        # part of what is being given away.
        if item.is_voided or item.is_comped:
            continue
        item.comped_at = now
        item.comp_reason = bill.nc_reason
        item.comped_by_user_id = user.id
    db.flush()

    bill = get_bill_or_404(db, business_id, bill_id)
    _recompute_totals(db, business_id, bill)

    # Zero outstanding means settled. _recompute_totals already lands on PAID
    # when amount_paid >= grand_total, and 0 >= 0; this is here so the
    # intention is explicit rather than an arithmetic coincidence.
    bill.status = BillStatus.PAID
    db.flush()

    if bill.location_id:
        location = db.get(Location, bill.location_id)
        if location is not None:
            location.status = LocationStatus.PAID
            db.flush()

    from app.services import kot_service

    # Held tickets are released the same as on a paid bill: the kitchen still
    # has to cook a staff meal. Loyalty is deliberately not accrued — points
    # are earned on money spent, and nothing was.
    kot_service.release_held_kots_for_session(db, business_id, bill.session_id)

    ws_manager.notify(business_id, "billing", "tables", "orders")
    return bill


def register_print(db: Session, business_id: uuid.UUID, bill_id: uuid.UUID) -> tuple[Bill, bool]:
    """Records that the bill was printed. Returns (bill, is_duplicate).

    The first print is the original; every one after it is a duplicate, which
    the renderer stamps on the paper. This is the standard control against
    the oldest till trick there is — printing two "originals" of one bill and
    pocketing one payment.
    """
    bill = get_bill_or_404(db, business_id, bill_id)
    is_first = bill.print_count == 0
    bill.print_count += 1
    if is_first:
        bill.first_printed_at = datetime.now(timezone.utc)
    db.flush()

    mark = toggles.is_enabled(db, business_id, toggles.MARK_DUPLICATE_REPRINT)
    return bill, (not is_first and mark)


def _accrue_loyalty_if_enabled(db: Session, business_id: uuid.UUID, bill: Bill) -> None:
    from app.models.enums import FeatureModule
    from app.models.feature_flag import FeatureFlag
    from app.services import loyalty_service

    flag = db.query(FeatureFlag).filter(
        FeatureFlag.business_id == business_id, FeatureFlag.module == FeatureModule.LOYALTY
    ).first()
    if flag is not None and flag.enabled:
        loyalty_service.process_paid_bill(db, business_id, bill)
