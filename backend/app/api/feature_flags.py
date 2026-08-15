from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_FULL_ACCESS
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.enums import FeatureModule, UserRole
from app.schemas.feature_flags import FeatureFlagOut, FeatureFlagUpdateRequest
from app.services import audit_service, feature_flag_service

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


@router.put("/features/{module}", response_model=FeatureFlagOut)
def update_feature(
    module: FeatureModule,
    payload: FeatureFlagUpdateRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    with transaction(db):
        flag = feature_flag_service.set_flag(db, business_id, module, payload.enabled)
        audit_service.record(
            db, action="feature_flag.update", business_id=business_id, user_id=user.id,
            resource_type="feature_flag", resource_id=module.value, metadata={"enabled": payload.enabled},
        )
    return FeatureFlagOut.model_validate(flag)
