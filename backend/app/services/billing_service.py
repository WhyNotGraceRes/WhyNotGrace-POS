import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.billing import Bill, BillDiscount, BillItem, BillServiceCharge, BillTax
from app.models.business import BusinessSettings
from app.models.enums import BillStatus, LocationStatus, OrderStatus
from app.models.location import Location
from app.models.order import Order, OrderSession
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
    subtotal = sum(float(i.line_total) for i in bill.items)
    tax_total = 0.0
    for tax in bill.taxes:
        tax.amount = round(subtotal * float(tax.percent) / 100, 2)
        tax_total += tax.amount
    service_total = 0.0
    for sc in bill.service_charges:
        sc.amount = round(subtotal * float(sc.percent) / 100, 2)
        service_total += sc.amount
    discount_total = sum(float(d.amount) for d in bill.discounts)

    bill.subtotal = round(subtotal, 2)
    bill.tax_total = round(tax_total, 2)
    bill.service_charge_total = round(service_total, 2)
    bill.discount_total = round(discount_total, 2)
    bill.grand_total = round(subtotal + tax_total + service_total - discount_total, 2)

    if bill.status not in (BillStatus.PAID, BillStatus.CANCELLED):
        if bill.amount_paid <= 0:
            bill.status = BillStatus.OPEN
        elif bill.amount_paid < bill.grand_total:
            bill.status = BillStatus.PARTIALLY_PAID
        else:
            bill.status = BillStatus.PAID


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
            db.add(
                BillTax(
                    business_id=business_id, bill_id=bill.id, name="Tax",
                    percent=settings_row.default_tax_percent, amount=0,
                )
            )

    if not bill.service_charges:
        if payload.service_charges:
            for sc in payload.service_charges:
                db.add(
                    BillServiceCharge(business_id=business_id, bill_id=bill.id, name=sc.name, percent=sc.percent, amount=0)
                )
        elif payload.use_default_service_charge and settings_row and settings_row.default_service_charge_percent > 0:
            db.add(
                BillServiceCharge(
                    business_id=business_id, bill_id=bill.id, name="Service Charge",
                    percent=settings_row.default_service_charge_percent, amount=0,
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
