"""Owner-facing configuration of value-based charge bands.

Owner-only, like the other money-shaping settings: a band silently adds to
what every guest pays, so it belongs with tax configuration rather than with
day-to-day menu editing.
"""
import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_FULL_ACCESS
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.business import BusinessSettings
from app.models.enums import ChargeBasis
from app.schemas.charge import (
    ChargeBandCreate,
    ChargeBandListOut,
    ChargeBandOut,
    ChargeBandUpdate,
    ChargeLadderGap,
    ChargePreviewLine,
    ChargePreviewOut,
    ChargePreviewRequest,
)
from app.services import audit_service, billing_service, charge_service

router = APIRouter(prefix="/charges", tags=["charges"])


@router.get("/bands", response_model=ChargeBandListOut)
def list_bands(
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    bands = charge_service.list_bands(db, business_id)

    gaps: list[ChargeLadderGap] = []
    for name, context in {(b.name, b.applies_to_context) for b in bands}:
        for lo, hi in charge_service.find_gaps(db, business_id, name, context):
            gaps.append(
                ChargeLadderGap(
                    name=name, applies_to_context=context,
                    from_amount=lo, to_amount=None if hi == float("inf") else hi,
                )
            )
    return ChargeBandListOut(bands=[ChargeBandOut.model_validate(b) for b in bands], gaps=gaps)


@router.post("/bands", response_model=ChargeBandOut, status_code=status.HTTP_201_CREATED)
def create_band(
    payload: ChargeBandCreate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    with transaction(db):
        band = charge_service.create_band(db, business_id, payload)
        audit_service.record(
            db, action="charge_band.create", business_id=business_id, user_id=user.id,
            resource_type="charge_band", resource_id=str(band.id),
        )
    return ChargeBandOut.model_validate(band)


@router.put("/bands/{band_id}", response_model=ChargeBandOut)
def update_band(
    band_id: uuid.UUID,
    payload: ChargeBandUpdate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    with transaction(db):
        band = charge_service.update_band(db, business_id, band_id, payload)
        audit_service.record(
            db, action="charge_band.update", business_id=business_id, user_id=user.id,
            resource_type="charge_band", resource_id=str(band.id),
        )
    return ChargeBandOut.model_validate(band)


@router.delete("/bands/{band_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_band(
    band_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    with transaction(db):
        charge_service.delete_band(db, business_id, band_id)
        audit_service.record(
            db, action="charge_band.delete", business_id=business_id, user_id=user.id,
            resource_type="charge_band", resource_id=str(band_id),
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/preview", response_model=ChargePreviewOut)
def preview(
    payload: ChargePreviewRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    """Shows what an order of a given value would actually be charged.

    Bands plus tax interact in ways that are hard to hold in your head — a
    taxable delivery fee changes the GST, a band boundary is half-open — so
    the owner gets to ask the system rather than reason it out and hope.
    Uses the same tax split the real bill uses, so what this shows is what
    the guest would pay.
    """
    bands = charge_service.select_bands_for(db, business_id, base=payload.amount, context=payload.context)

    lines: list[ChargePreviewLine] = []
    charges_total = 0.0
    taxable_charges = 0.0
    for band in bands:
        amount = (
            round(payload.amount * float(band.value) / 100, 2)
            if band.basis == ChargeBasis.PERCENT
            else float(band.value)
        )
        lines.append(
            ChargePreviewLine(
                name=band.name, basis=band.basis, value=float(band.value),
                amount=amount, is_taxable=band.is_taxable,
            )
        )
        charges_total += amount
        if band.is_taxable:
            taxable_charges += amount

    settings_row = db.query(BusinessSettings).filter(BusinessSettings.business_id == business_id).first()
    taxable_value = payload.amount + taxable_charges

    tax_lines: list[dict] = []
    tax_total = 0.0
    if settings_row and settings_row.default_tax_percent > 0:
        for name, percent in billing_service._tax_components(settings_row):
            amount = round(taxable_value * percent / 100, 2)
            tax_lines.append({"name": name, "percent": percent, "amount": amount})
            tax_total += amount

    return ChargePreviewOut(
        amount=payload.amount,
        charges=lines,
        charges_total=round(charges_total, 2),
        taxable_value=round(taxable_value, 2),
        tax_lines=tax_lines,
        tax_total=round(tax_total, 2),
        grand_total=round(payload.amount + charges_total + tax_total, 2),
    )
