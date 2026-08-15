import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.billing import Bill, BillDiscount, BillItem, BillServiceCharge, BillTax
from app.models.business import BusinessSettings
from app.models.enums import BillStatus, ChargeBasis, LocationStatus, OrderStatus, PricingContext
from app.models.location import Location
from app.models.order import Order, OrderSession
from app.services import charge_service
from app.utils.numbering import generate_number


def _bill_query(db: Session, business_id: uuid.UUID):
    return (
        db.query(Bill)
        .populate_existing()
        .options(
            joinedload(Bill.items), joinedload(Bill.taxes), joinedload(Bill.discounts), joinedload(Bill.service_charges)
        )
        .filter(Bill.business_id == business_id)
    )


def get_bill_or_404(db: Session, business_id: uuid.UUID, bill_id: uuid.UUID) -> Bill:
    bill = _bill_query(db, business_id).filter(Bill.id == bill_id).first()
    if bill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return bill


def _recompute_totals(bill: Bill) -> None:
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
    subtotal = sum(float(i.line_total) for i in bill.items)
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

    bill.subtotal = round(subtotal, 2)
    bill.tax_total = round(tax_total, 2)
    bill.service_charge_total = round(charges_total, 2)
    bill.discount_total = round(discount_total, 2)
    bill.grand_total = round(taxable_base + charges_total + tax_total, 2)

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
    _recompute_totals(bill)
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
    _recompute_totals(bill)
    db.flush()
    return bill


def record_payment_applied(db: Session, business_id: uuid.UUID, bill_id: uuid.UUID, amount: float) -> Bill:
    bill = get_bill_or_404(db, business_id, bill_id)
    was_paid_before = bill.status == BillStatus.PAID
    bill.amount_paid = round(float(bill.amount_paid) + amount, 2)
    _recompute_totals(bill)
    db.flush()

    if bill.status == BillStatus.PAID and bill.location_id:
        location = db.get(Location, bill.location_id)
        if location is not None:
            location.status = LocationStatus.PAID
            db.flush()

    if bill.status == BillStatus.PAID and not was_paid_before:
        from app.services import kot_service

        kot_service.release_held_kots_for_session(db, business_id, bill.session_id)
        _accrue_loyalty_if_enabled(db, business_id, bill)

    return bill


def _accrue_loyalty_if_enabled(db: Session, business_id: uuid.UUID, bill: Bill) -> None:
    from app.models.enums import FeatureModule
    from app.models.feature_flag import FeatureFlag
    from app.services import loyalty_service

    flag = db.query(FeatureFlag).filter(
        FeatureFlag.business_id == business_id, FeatureFlag.module == FeatureModule.LOYALTY
    ).first()
    if flag is not None and flag.enabled:
        loyalty_service.process_paid_bill(db, business_id, bill)
