import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.platform_dependencies import get_current_platform_user
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.platform_user import PlatformUser
from app.schemas.platform import (
    PlatformBusinessOut,
    ProvisionBusinessRequest,
    ProvisionBusinessResponse,
    SetBusinessActiveRequest,
)
from app.services import platform_service

router = APIRouter(prefix="/platform/businesses", tags=["platform-businesses"])


@router.get("", response_model=list[PlatformBusinessOut])
def list_businesses(
    db: Session = Depends(get_db),
    _platform_user: PlatformUser = Depends(get_current_platform_user),
):
    return [PlatformBusinessOut.model_validate(b) for b in platform_service.list_businesses(db)]


@router.post("", response_model=ProvisionBusinessResponse, status_code=status.HTTP_201_CREATED)
def provision_business(
    payload: ProvisionBusinessRequest,
    db: Session = Depends(get_db),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    with transaction(db):
        owner = platform_service.provision_business(db, payload, platform_user.id)
    return ProvisionBusinessResponse(business_id=owner.business_id, owner_user_id=owner.id, owner_email=owner.email)


@router.get("/{business_id}", response_model=PlatformBusinessOut)
def get_business(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    _platform_user: PlatformUser = Depends(get_current_platform_user),
):
    return PlatformBusinessOut.model_validate(platform_service.get_business_or_404(db, business_id))


@router.put("/{business_id}/active", response_model=PlatformBusinessOut)
def set_business_active(
    business_id: uuid.UUID,
    payload: SetBusinessActiveRequest,
    db: Session = Depends(get_db),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    """The manual kill-switch — see platform_service.set_business_active."""
    with transaction(db):
        business = platform_service.set_business_active(
            db, business_id, is_active=payload.is_active, platform_user_id=platform_user.id
        )
    return PlatformBusinessOut.model_validate(business)
