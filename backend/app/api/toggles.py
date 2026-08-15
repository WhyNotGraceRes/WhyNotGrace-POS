"""Fine-grained behaviour switches.

Readable by any staff member, because the UI needs to know what is on to
render correctly. Writable only by an owner — these change what the counter
does, and several of them weaken an audit trail.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_FULL_ACCESS
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.enums import UserRole
from app.models.invoice import InvoiceCounter
from app.schemas.toggle import InvoiceSeriesOut, ToggleOut, ToggleUpdateRequest
from app.services import audit_service, invoice_service, toggle_service

router = APIRouter(prefix="/settings", tags=["toggles"])


def _to_out(definition, enabled: bool, is_overridden: bool) -> ToggleOut:
    return ToggleOut(
        key=definition.key,
        group=definition.group,
        enabled=enabled,
        is_overridden=is_overridden,
        default=definition.default,
        owner_editable=definition.owner_editable,
        label=definition.label,
        description=definition.description,
        warning=definition.warning,
    )


@router.get("/toggles", response_model=list[ToggleOut])
def list_toggles(
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*UserRole)),
):
    return [
        _to_out(d, enabled, overridden)
        for d, enabled, overridden in toggle_service.list_effective(db, business_id)
    ]


@router.put("/toggles/{key}", response_model=ToggleOut)
def update_toggle(
    key: str,
    payload: ToggleUpdateRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    with transaction(db):
        definition, enabled = toggle_service.set_toggle(db, business_id, key, payload.enabled)
        audit_service.record(
            db, action="toggle.update", business_id=business_id, user_id=user.id,
            resource_type="toggle", resource_id=key, metadata={"enabled": enabled},
        )
    return _to_out(definition, enabled, True)


@router.delete("/toggles/{key}", response_model=ToggleOut)
def reset_toggle(
    key: str,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    """Clears the override so this business follows the default again."""
    with transaction(db):
        definition = toggle_service.reset_toggle(db, business_id, key)
        audit_service.record(
            db, action="toggle.reset", business_id=business_id, user_id=user.id,
            resource_type="toggle", resource_id=key,
        )
    return _to_out(definition, definition.default, False)


@router.get("/invoice-series", response_model=InvoiceSeriesOut)
def invoice_series(
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    fy = invoice_service.financial_year_code()
    counter = (
        db.query(InvoiceCounter)
        .filter(
            InvoiceCounter.business_id == business_id,
            InvoiceCounter.series == invoice_service.DEFAULT_SERIES,
        )
        .order_by(InvoiceCounter.financial_year.desc())
        .first()
    )
    return InvoiceSeriesOut(
        series=invoice_service.DEFAULT_SERIES,
        financial_year=counter.financial_year if counter else fy,
        next_number=invoice_service.peek_next(db, business_id),
        last_issued=counter.last_number if counter else 0,
    )
