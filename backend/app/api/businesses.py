from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business, require_roles
from app.core.permissions import ROLE_FULL_ACCESS
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.business import Business
from app.schemas.business import BusinessOut, BusinessUpdateRequest
from app.services import audit_service

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.get("/me", response_model=BusinessOut)
def get_my_business(business: Business = Depends(get_current_business)):
    return BusinessOut.model_validate(business)


@router.put("/me", response_model=BusinessOut)
def update_my_business(
    payload: BusinessUpdateRequest,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    with transaction(db):
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(business, field, value)
        db.flush()
        audit_service.record(
            db, action="business.update", business_id=business.id, user_id=user.id,
            resource_type="business", resource_id=str(business.id),
        )
    return BusinessOut.model_validate(business)
