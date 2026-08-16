import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.platform_dependencies import get_current_platform_user
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.enums import FeatureModule
from app.models.platform_user import PlatformUser
from app.schemas.feature_flags import FeatureFlagOut
from app.schemas.platform import PlatformFeatureFlagUpdateRequest
from app.services import audit_service, feature_flag_service, platform_service

router = APIRouter(prefix="/platform/businesses/{business_id}/features", tags=["platform-features"])


@router.get("", response_model=list[FeatureFlagOut])
def list_features(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    _platform_user: PlatformUser = Depends(get_current_platform_user),
):
    platform_service.get_business_or_404(db, business_id)
    return [FeatureFlagOut.model_validate(f) for f in feature_flag_service.list_flags(db, business_id)]


@router.put("/{module}", response_model=FeatureFlagOut)
def set_feature(
    business_id: uuid.UUID,
    module: FeatureModule,
    payload: PlatformFeatureFlagUpdateRequest,
    db: Session = Depends(get_db),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    """The only writer of FeatureFlag rows — see app.api.feature_flags,
    where the equivalent owner-facing endpoint was removed."""
    with transaction(db):
        platform_service.get_business_or_404(db, business_id)
        flag = feature_flag_service.set_flag(db, business_id, module, payload.enabled)
        audit_service.record(
            db, action="platform.feature_flag_update", business_id=business_id, platform_user_id=platform_user.id,
            resource_type="feature_flag", resource_id=module.value, metadata={"enabled": payload.enabled},
        )
    return FeatureFlagOut.model_validate(flag)
