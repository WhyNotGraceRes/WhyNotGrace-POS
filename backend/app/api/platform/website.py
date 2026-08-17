import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.platform_dependencies import get_current_platform_user
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.platform_user import PlatformUser
from app.schemas.website import WebsiteConfigOut, WebsiteConfigUpdateRequest
from app.services import audit_service, platform_service, website_service

router = APIRouter(prefix="/platform/businesses/{business_id}/website", tags=["platform-website"])


@router.get("", response_model=WebsiteConfigOut)
def get_website(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    _platform_user: PlatformUser = Depends(get_current_platform_user),
):
    platform_service.get_business_or_404(db, business_id)
    return WebsiteConfigOut.model_validate(website_service.get_or_create_config(db, business_id))


@router.put("", response_model=WebsiteConfigOut)
def update_website(
    business_id: uuid.UUID,
    payload: WebsiteConfigUpdateRequest,
    db: Session = Depends(get_db),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    """The onboarding-time content editor: pasting in a logo/hero image
    URL, the restaurant's story, a theme color, and publishing — the
    "we paste images and menu, they get their site" step. The owner's own
    PUT /website/config (app/api/website.py) still exists for a business
    that wants to maintain its own content later; this is the same
    underlying config, just writable by platform staff too."""
    with transaction(db):
        platform_service.get_business_or_404(db, business_id)
        config = website_service.update_config(db, business_id, payload)
        audit_service.record(
            db, action="platform.website_config_update", business_id=business_id,
            platform_user_id=platform_user.id, resource_type="website_config",
        )
    return WebsiteConfigOut.model_validate(config)
