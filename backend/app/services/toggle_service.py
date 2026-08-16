"""Reading and writing per-business toggle overrides."""
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core import toggles
from app.core.toggles import ToggleDef
from app.models.toggle import BusinessToggle


def list_effective(db: Session, business_id: uuid.UUID) -> list[tuple[ToggleDef, bool, bool]]:
    """Every registered toggle with its effective value.

    Returns (definition, enabled, is_overridden). The third element lets the
    UI distinguish "the owner chose this" from "this is the default", which
    matters when a default later changes: a business that never expressed a
    preference should follow the new default, and the screen should not imply
    they picked it.
    """
    overrides = {
        row.key: row.enabled
        for row in db.query(BusinessToggle).filter(BusinessToggle.business_id == business_id).all()
    }
    out = []
    for definition in toggles.all_toggles():
        if definition.key in overrides:
            out.append((definition, overrides[definition.key], True))
        else:
            out.append((definition, definition.default, False))
    return out


def _upsert(db: Session, business_id: uuid.UUID, key: str, enabled: bool) -> None:
    row = (
        db.query(BusinessToggle)
        .filter(BusinessToggle.business_id == business_id, BusinessToggle.key == key)
        .first()
    )
    if row is None:
        row = BusinessToggle(business_id=business_id, key=key, enabled=enabled)
        db.add(row)
    else:
        row.enabled = enabled
    db.flush()


def set_toggle(db: Session, business_id: uuid.UUID, key: str, enabled: bool) -> tuple[ToggleDef, bool]:
    """The owner-facing writer. Refuses to touch an entitlement toggle —
    see platform_set_toggle for the one path that can."""
    definition = toggles.get_def(key)
    if definition is None:
        # The key column is a free string so that adding a switch needs no
        # migration; this check is what stops that looseness from becoming a
        # way to write arbitrary rows.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown setting: {key}")

    if not definition.owner_editable:
        # An entitlement. If an owner could flip these, "pay only for what
        # you need" would stop meaning anything.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "This is part of your plan and cannot be changed here. "
                "Contact support to change what your plan includes."
            ),
        )

    _upsert(db, business_id, key, enabled)
    return definition, enabled


def platform_set_toggle(db: Session, business_id: uuid.UUID, key: str, enabled: bool) -> tuple[ToggleDef, bool]:
    """The platform-facing writer, called only from behind
    get_current_platform_user (see app.api.platform.toggles). Deliberately
    has no owner_editable check — that gate exists to stop a BUSINESS from
    changing its own entitlements, not to stop the platform that grants them.
    """
    definition = toggles.get_def(key)
    if definition is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown setting: {key}")
    _upsert(db, business_id, key, enabled)
    return definition, enabled


def reset_toggle(db: Session, business_id: uuid.UUID, key: str) -> ToggleDef:
    """Drops the override so the business follows the registry default again."""
    definition = toggles.get_def(key)
    if definition is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown setting: {key}")
    if not definition.owner_editable:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This is part of your plan and cannot be changed here.",
        )
    db.query(BusinessToggle).filter(
        BusinessToggle.business_id == business_id, BusinessToggle.key == key
    ).delete()
    db.flush()
    return definition
