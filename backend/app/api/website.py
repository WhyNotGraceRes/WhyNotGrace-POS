from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_feature, require_roles
from app.core.permissions import ROLE_FULL_ACCESS
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.enums import FeatureModule
from app.schemas.website import PublicWebsiteResponse, WebsiteConfigOut, WebsiteConfigUpdateRequest
from app.services import audit_service, website_service

router = APIRouter(prefix="/website", tags=["website"])


@router.get(
    "/config", response_model=WebsiteConfigOut, dependencies=[Depends(require_feature(FeatureModule.ONLINE_WEBSITE))]
)
def get_config(business_id=Depends(get_current_business_id), db: Session = Depends(get_db)):
    return WebsiteConfigOut.model_validate(website_service.get_or_create_config(db, business_id))


@router.put(
    "/config", response_model=WebsiteConfigOut, dependencies=[Depends(require_feature(FeatureModule.ONLINE_WEBSITE))]
)
def update_config(
    payload: WebsiteConfigUpdateRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    with transaction(db):
        config = website_service.update_config(db, business_id, payload)
        audit_service.record(
            db, action="website_config.update", business_id=business_id, user_id=user.id, resource_type="website_config"
        )
    return WebsiteConfigOut.model_validate(config)


@router.get("/public/{business_slug}", response_model=PublicWebsiteResponse)
def get_public_website(business_slug: str, db: Session = Depends(get_db)):
    business, config, pickup_enabled, delivery_enabled = website_service.get_public_website(db, business_slug)
    return PublicWebsiteResponse(
        business_id=business.id,
        business_name=business.name,
        business_type=business.business_type.value,
        config=WebsiteConfigOut.model_validate(config),
        pickup_enabled=pickup_enabled,
        delivery_enabled=delivery_enabled,
    )
