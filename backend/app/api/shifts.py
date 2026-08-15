"""Cash drawer sessions.

Opening and closing are available to anyone who handles money
(ROLE_BILLING), because the person on the counter is the person who counts
the drawer. Listing other people's shifts is ROLE_OPERATIONAL — a cashier
seeing every other cashier's variance is how a shortfall gets quietly
"explained" before anyone in charge sees it.
"""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_BILLING, ROLE_OPERATIONAL
from app.database.session import get_db
from app.database.transaction import transaction
from app.schemas.shift import (
    CloseShiftRequest,
    OpenShiftRequest,
    ShiftOut,
    ShiftReportOut,
)
from app.services import audit_service, shift_service

router = APIRouter(prefix="/shifts", tags=["shifts"])


@router.get("/current", response_model=ShiftOut | None)
def current_shift(
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_BILLING)),
):
    """This user's own open drawer, or null. Drives whether the UI offers
    Open or Close."""
    shift = shift_service.get_open_shift(db, business_id, user.id)
    return ShiftOut.model_validate(shift) if shift else None


@router.post("", response_model=ShiftOut, status_code=status.HTTP_201_CREATED)
def open_shift(
    payload: OpenShiftRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_BILLING)),
):
    with transaction(db):
        shift = shift_service.open_shift(db, business_id, user.id, opening_float=payload.opening_float)
        audit_service.record(
            db, action="shift.open", business_id=business_id, user_id=user.id,
            resource_type="shift", resource_id=str(shift.id),
            metadata={"opening_float": float(shift.opening_float)},
        )
    return ShiftOut.model_validate(shift)


@router.post("/{shift_id}/close", response_model=ShiftReportOut)
def close_shift(
    shift_id: uuid.UUID,
    payload: CloseShiftRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_BILLING)),
):
    """Closes against a counted amount and returns the Z-report.

    The counted figure is part of the request, so it is committed before the
    response reveals what was expected. That ordering is the blind count —
    reversing it would let a cashier read the expected amount and type it
    back.
    """
    with transaction(db):
        shift = shift_service.close_shift(
            db, business_id, shift_id, user.id,
            declared_cash=payload.declared_cash, notes=payload.notes,
        )
        audit_service.record(
            db, action="shift.close", business_id=business_id, user_id=user.id,
            resource_type="shift", resource_id=str(shift.id),
            metadata={
                "declared_cash": float(shift.declared_cash),
                "expected_cash": float(shift.expected_cash),
                "variance": float(shift.variance),
            },
        )
        report = shift_service.build_report(db, business_id, shift)
    return ShiftReportOut.model_validate(report)


@router.get("/{shift_id}/report", response_model=ShiftReportOut)
def shift_report(
    shift_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_BILLING)),
):
    """The Z-report. On an open shift with blind counting on, the expected
    cash comes back null — everything else is visible."""
    shift = shift_service.get_shift_or_404(db, business_id, shift_id)
    return ShiftReportOut.model_validate(shift_service.build_report(db, business_id, shift))


@router.get("", response_model=list[ShiftOut])
def list_shifts(
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    return [ShiftOut.model_validate(s) for s in shift_service.list_shifts(db, business_id)]
