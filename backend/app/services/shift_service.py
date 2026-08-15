"""Opening, closing and reporting on cash drawers."""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import toggles
from app.models.billing import Bill, BillDiscount
from app.models.enums import BillStatus, PaymentMethod, PaymentStatus
from app.models.payment import Payment
from app.models.refund import Refund
from app.models.shift import ShiftSession, ShiftStatus
from app.models.user import User


def get_open_shift(db: Session, business_id: uuid.UUID, user_id: uuid.UUID) -> ShiftSession | None:
    return (
        db.query(ShiftSession)
        .filter(
            ShiftSession.business_id == business_id,
            ShiftSession.opened_by_user_id == user_id,
            ShiftSession.status == ShiftStatus.OPEN,
        )
        .order_by(ShiftSession.opened_at.desc())
        .first()
    )


def open_shift(db: Session, business_id: uuid.UUID, user_id: uuid.UUID, *, opening_float: float) -> ShiftSession:
    """Starts a drawer for this cashier.

    Refuses a second one. Two open drawers for the same person means every
    payment they take has to guess which it belongs to, and a shortfall in
    one can always be explained away as a surplus in the other.
    """
    if get_open_shift(db, business_id, user_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an open shift. Close it before starting another.",
        )

    shift = ShiftSession(
        business_id=business_id,
        status=ShiftStatus.OPEN,
        opened_by_user_id=user_id,
        opened_at=datetime.now(timezone.utc),
        opening_float=round(float(opening_float), 2),
    )
    db.add(shift)
    db.flush()
    return shift


def get_shift_or_404(db: Session, business_id: uuid.UUID, shift_id: uuid.UUID) -> ShiftSession:
    shift = (
        db.query(ShiftSession)
        .filter(ShiftSession.id == shift_id, ShiftSession.business_id == business_id)
        .first()
    )
    if shift is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
    return shift


def _cash_movement(db: Session, shift: ShiftSession) -> tuple[float, float]:
    """(cash taken, cash returned) for this drawer.

    Cash only, deliberately. A card or UPI payment never enters the drawer,
    so counting it would produce an expected figure no honest cashier could
    ever match.
    """
    taken = float(
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.shift_id == shift.id,
            Payment.status == PaymentStatus.SUCCESS,
            Payment.method == PaymentMethod.CASH,
        )
        .scalar()
    )
    returned = float(
        db.query(func.coalesce(func.sum(Refund.amount), 0))
        .filter(Refund.shift_id == shift.id, Refund.method == PaymentMethod.CASH)
        .scalar()
    )
    return round(taken, 2), round(returned, 2)


def expected_cash(db: Session, shift: ShiftSession) -> float:
    taken, returned = _cash_movement(db, shift)
    return round(float(shift.opening_float) + taken - returned, 2)


def close_shift(
    db: Session,
    business_id: uuid.UUID,
    shift_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    declared_cash: float,
    notes: str | None = None,
) -> ShiftSession:
    """Closes the drawer against a counted amount.

    The count arrives before this function reveals anything, which is the
    entire point of the blind-count design: a cashier shown the expected
    figure first will type that number, and the control stops controlling
    anything.
    """
    shift = get_shift_or_404(db, business_id, shift_id)
    if shift.status == ShiftStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Shift is already closed")

    expected = expected_cash(db, shift)
    declared = round(float(declared_cash), 2)

    shift.declared_cash = declared
    shift.expected_cash = expected
    shift.variance = round(declared - expected, 2)
    shift.closed_at = datetime.now(timezone.utc)
    shift.closed_by_user_id = user_id
    shift.status = ShiftStatus.CLOSED
    shift.notes = (notes or "").strip() or None
    db.flush()
    return shift


def build_report(db: Session, business_id: uuid.UUID, shift: ShiftSession) -> dict:
    """The Z-report.

    Everything here is scoped by shift_id rather than by a time window. Those
    look equivalent and are not — a payment recorded a second after close, or
    across a clock adjustment, lands in the wrong drawer with nothing to show
    it moved.
    """
    by_method = [
        {"method": method.value, "count": count, "amount": round(float(total), 2)}
        for method, count, total in db.query(
            Payment.method, func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0)
        )
        .filter(Payment.shift_id == shift.id, Payment.status == PaymentStatus.SUCCESS)
        .group_by(Payment.method)
        .all()
    ]

    refunds_total = float(
        db.query(func.coalesce(func.sum(Refund.amount), 0))
        .filter(Refund.shift_id == shift.id)
        .scalar()
    )
    refunds_count = int(
        db.query(func.count(Refund.id)).filter(Refund.shift_id == shift.id).scalar()
    )

    bill_ids = [
        row[0]
        for row in db.query(Payment.bill_id).filter(Payment.shift_id == shift.id).distinct().all()
    ]

    # Voids and discounts are what an owner scans this report for. A drawer
    # that balances perfectly while ten bills were voided is not a drawer
    # that balanced.
    voided = 0
    discounts_total = 0.0
    if bill_ids:
        voided = int(
            db.query(func.count(Bill.id))
            .filter(Bill.id.in_(bill_ids), Bill.status == BillStatus.CANCELLED)
            .scalar()
        )
        discounts_total = float(
            db.query(func.coalesce(func.sum(BillDiscount.amount), 0))
            .filter(BillDiscount.bill_id.in_(bill_ids))
            .scalar()
        )

    taken, returned = _cash_movement(db, shift)
    opened_by = db.get(User, shift.opened_by_user_id) if shift.opened_by_user_id else None

    is_closed = shift.status == ShiftStatus.CLOSED
    blind = toggles.is_enabled(db, business_id, toggles.BLIND_CASH_COUNT)

    return {
        "shift_id": shift.id,
        "status": shift.status.value,
        "opened_at": shift.opened_at,
        "closed_at": shift.closed_at,
        "opened_by": f"{opened_by.first_name} {opened_by.last_name}".strip() if opened_by else None,
        "opening_float": round(float(shift.opening_float), 2),
        "payments": sorted(by_method, key=lambda p: p["method"]),
        "gross_takings": round(sum(p["amount"] for p in by_method), 2),
        "cash_taken": taken,
        "cash_returned": returned,
        "refunds_count": refunds_count,
        "refunds_total": round(refunds_total, 2),
        "bills_settled": len(bill_ids),
        "bills_voided": voided,
        "discounts_total": round(discounts_total, 2),
        # Withheld while the shift is open and blind counting is on. This is
        # the control: the number is not secret afterwards, it is only
        # unavailable at the one moment when seeing it would let the cashier
        # copy it instead of counting.
        "expected_cash": (
            round(float(shift.expected_cash), 2)
            if is_closed and shift.expected_cash is not None
            else (None if blind else expected_cash(db, shift))
        ),
        "declared_cash": round(float(shift.declared_cash), 2) if shift.declared_cash is not None else None,
        "variance": round(float(shift.variance), 2) if shift.variance is not None else None,
        "blind_count": blind,
        "notes": shift.notes,
    }


def list_shifts(db: Session, business_id: uuid.UUID, *, limit: int = 50) -> list[ShiftSession]:
    return (
        db.query(ShiftSession)
        .filter(ShiftSession.business_id == business_id)
        .order_by(ShiftSession.opened_at.desc())
        .limit(limit)
        .all()
    )
