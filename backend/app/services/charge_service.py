"""Owner-defined charge bands: CRUD, validation, and selection at bill time.

The validation here is doing more work than it looks. Bands are the kind of
configuration an owner sets up once, gets subtly wrong, and then never
inspects again — so a ladder with two rows covering ₹200, or a gap at
₹100.50, would quietly mis-bill every affected order for months. Overlaps
are therefore rejected at write time rather than resolved by some
tie-breaking rule at bill time, because a tie-breaking rule is exactly the
kind of behaviour nobody can predict from looking at the screen.
"""
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.charge import ChargeBand
from app.models.enums import ChargeBasis, PricingContext


def _ladder(db: Session, business_id: uuid.UUID, name: str, context: PricingContext | None):
    """Every band sharing a name and context — one ladder."""
    query = db.query(ChargeBand).filter(
        ChargeBand.business_id == business_id, ChargeBand.name == name
    )
    if context is None:
        query = query.filter(ChargeBand.applies_to_context.is_(None))
    else:
        query = query.filter(ChargeBand.applies_to_context == context)
    return query


def _overlaps(a_min: float, a_max: float | None, b_min: float, b_max: float | None) -> bool:
    """Half-open intervals [min, max) overlap unless one ends at or before
    the other begins. A NULL max is treated as infinity."""
    a_hi = float("inf") if a_max is None else a_max
    b_hi = float("inf") if b_max is None else b_max
    return a_min < b_hi and b_min < a_hi


def validate_band(
    db: Session,
    business_id: uuid.UUID,
    *,
    name: str,
    context: PricingContext | None,
    min_amount: float,
    max_amount: float | None,
    exclude_id: uuid.UUID | None = None,
) -> None:
    if max_amount is not None and max_amount <= min_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The band's upper bound must be greater than its lower bound.",
        )
    if min_amount < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="A band cannot start below zero."
        )

    for other in _ladder(db, business_id, name, context).all():
        if exclude_id is not None and other.id == exclude_id:
            continue
        if _overlaps(min_amount, max_amount, float(other.min_amount),
                     None if other.max_amount is None else float(other.max_amount)):
            other_hi = "and above" if other.max_amount is None else f"to under {other.max_amount}"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"This band overlaps an existing '{name}' band ({other.min_amount} {other_hi}). "
                    "Two bands of the same charge cannot both apply to one order — "
                    "adjust the range so they meet without overlapping."
                ),
            )


def find_gaps(db: Session, business_id: uuid.UUID, name: str, context: PricingContext | None) -> list[tuple[float, float]]:
    """Uncovered stretches in a ladder, as (from, to) pairs.

    Not an error — an owner may legitimately want a charge that only applies
    between ₹100 and ₹500 and nowhere else. It is surfaced in the API
    response so the admin screen can point out the more likely case, which
    is that they meant to cover the whole range and mistyped a boundary.
    """
    bands = sorted(_ladder(db, business_id, name, context).all(), key=lambda b: float(b.min_amount))
    if not bands:
        return []

    gaps: list[tuple[float, float]] = []
    cursor = 0.0
    for band in bands:
        low = float(band.min_amount)
        if low > cursor:
            gaps.append((cursor, low))
        if band.max_amount is None:
            return gaps  # open-ended top: everything above is covered
        cursor = max(cursor, float(band.max_amount))
    gaps.append((cursor, float("inf")))
    return gaps


def list_bands(db: Session, business_id: uuid.UUID) -> list[ChargeBand]:
    return (
        db.query(ChargeBand)
        .filter(ChargeBand.business_id == business_id)
        .order_by(ChargeBand.name, ChargeBand.display_order, ChargeBand.min_amount)
        .all()
    )


def get_band_or_404(db: Session, business_id: uuid.UUID, band_id: uuid.UUID) -> ChargeBand:
    band = db.query(ChargeBand).filter(
        ChargeBand.id == band_id, ChargeBand.business_id == business_id
    ).first()
    if band is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Charge band not found")
    return band


def create_band(db: Session, business_id: uuid.UUID, payload) -> ChargeBand:
    validate_band(
        db, business_id, name=payload.name, context=payload.applies_to_context,
        min_amount=payload.min_amount, max_amount=payload.max_amount,
    )
    band = ChargeBand(
        business_id=business_id, name=payload.name, applies_to_context=payload.applies_to_context,
        min_amount=payload.min_amount, max_amount=payload.max_amount,
        basis=payload.basis, value=payload.value, is_taxable=payload.is_taxable,
        is_active=payload.is_active, display_order=payload.display_order,
    )
    db.add(band)
    db.flush()
    return band


def update_band(db: Session, business_id: uuid.UUID, band_id: uuid.UUID, payload) -> ChargeBand:
    band = get_band_or_404(db, business_id, band_id)
    data = payload.model_dump(exclude_unset=True)

    validate_band(
        db, business_id,
        name=data.get("name", band.name),
        context=data.get("applies_to_context", band.applies_to_context),
        min_amount=data.get("min_amount", float(band.min_amount)),
        max_amount=data.get("max_amount", None if band.max_amount is None else float(band.max_amount)),
        exclude_id=band.id,
    )
    for field, value in data.items():
        setattr(band, field, value)
    db.flush()
    return band


def delete_band(db: Session, business_id: uuid.UUID, band_id: uuid.UUID) -> None:
    band = get_band_or_404(db, business_id, band_id)
    db.delete(band)
    db.flush()


def select_bands_for(
    db: Session, business_id: uuid.UUID, *, base: float, context: PricingContext | None
) -> list[ChargeBand]:
    """One matching band per ladder, for a bill whose discounted value is
    `base`.

    A band whose applies_to_context is NULL matches every context. When both
    a context-specific ladder and a global one share a name, the
    context-specific one wins — the more specific configuration is the one
    the owner set up deliberately for this fulfilment type.
    """
    candidates = (
        db.query(ChargeBand)
        .filter(ChargeBand.business_id == business_id, ChargeBand.is_active.is_(True))
        .order_by(ChargeBand.display_order, ChargeBand.name)
        .all()
    )

    chosen: dict[str, ChargeBand] = {}
    for band in candidates:
        if band.applies_to_context is not None and band.applies_to_context != context:
            continue
        low = float(band.min_amount)
        high = float("inf") if band.max_amount is None else float(band.max_amount)
        if not (low <= base < high):
            continue
        current = chosen.get(band.name)
        if current is None or (current.applies_to_context is None and band.applies_to_context is not None):
            chosen[band.name] = band

    # A zero-value band is how "free above ₹500" is expressed. It is dropped
    # here rather than added as a ₹0 line, so the bill does not carry
    # "Delivery charge  ₹0" — which reads to a guest like a mistake.
    return [b for b in chosen.values() if float(b.value) != 0]
