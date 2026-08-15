import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import ALWAYS_ON_FEATURES, FeatureModule
from app.models.feature_flag import FeatureFlag


def list_flags(db: Session, business_id: uuid.UUID) -> list[FeatureFlag]:
    existing = {
        f.module: f
        for f in db.query(FeatureFlag).filter(FeatureFlag.business_id == business_id).all()
    }
    # Self-heal: if a module was added after a business registered, backfill it.
    result = []
    for module in FeatureModule:
        flag = existing.get(module)
        if flag is None:
            flag = FeatureFlag(business_id=business_id, module=module, enabled=module in ALWAYS_ON_FEATURES)
            db.add(flag)
            db.flush()
        result.append(flag)
    return result


def set_flag(db: Session, business_id: uuid.UUID, module: FeatureModule, enabled: bool) -> FeatureFlag:
    if module in ALWAYS_ON_FEATURES and not enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"{module.value} cannot be disabled"
        )
    flag = (
        db.query(FeatureFlag)
        .filter(FeatureFlag.business_id == business_id, FeatureFlag.module == module)
        .first()
    )
    if flag is None:
        flag = FeatureFlag(business_id=business_id, module=module, enabled=enabled)
        db.add(flag)
    else:
        flag.enabled = enabled
    db.flush()
    return flag
