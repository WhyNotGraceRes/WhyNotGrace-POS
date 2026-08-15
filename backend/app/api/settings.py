from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_FULL_ACCESS
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.business import BusinessSettings
from app.schemas.settings import BusinessSettingsOut, BusinessSettingsUpdateRequest
from app.services import audit_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=BusinessSettingsOut)
def get_settings_(business_id=Depends(get_current_business_id), db: Session = Depends(get_db)):
    settings = db.query(BusinessSettings).filter(BusinessSettings.business_id == business_id).first()
    if settings is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not found")
    return BusinessSettingsOut.model_validate(settings)


@router.put("", response_model=BusinessSettingsOut)
def update_settings(
    payload: BusinessSettingsUpdateRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    with transaction(db):
        settings = db.query(BusinessSettings).filter(BusinessSettings.business_id == business_id).first()
        if settings is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settings not found")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(settings, field, value)
        db.flush()
        audit_service.record(
            db, action="settings.update", business_id=business_id, user_id=user.id, resource_type="business_settings"
        )
    return BusinessSettingsOut.model_validate(settings)
