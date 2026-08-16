"""Read-only for a business's own staff. What a business is entitled to is
platform-controlled — see app.api.platform.features for the only writer of
FeatureFlag rows, gated behind get_current_platform_user rather than any
business role. Until this write path was removed, an owner could self-enable
every paid module here for free, since the only check was "are you OWNER of
your own business" — no entitlement gate at all.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.enums import UserRole
from app.schemas.feature_flags import FeatureFlagOut
from app.services import feature_flag_service

router = APIRouter(tags=["feature-flags"])


@router.get("/features", response_model=list[FeatureFlagOut])
def get_features(
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*UserRole)),
):
    with transaction(db):
        flags = feature_flag_service.list_flags(db, business_id)
    return [FeatureFlagOut.model_validate(f) for f in flags]
