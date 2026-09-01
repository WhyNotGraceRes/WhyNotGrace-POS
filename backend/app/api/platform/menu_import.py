import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.platform_dependencies import get_current_platform_user
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.platform_user import PlatformUser
from app.schemas.menu_import import MenuImportExtractResponse, MenuImportPublishRequest, MenuImportPublishResponse
from app.services import audit_service, menu_import_service, menu_service, platform_service

router = APIRouter(prefix="/platform/businesses/{business_id}/menu-import", tags=["platform-menu-import"])


@router.post("/extract", response_model=MenuImportExtractResponse)
def extract_menu(
    business_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    _platform_user: PlatformUser = Depends(get_current_platform_user),
):
    """Step 1 of 2: upload photo(s) of the restaurant's physical menu card,
    get back a structured draft — nothing is written to the real menu yet.
    See menu_import_service for the extraction model call, and /publish
    below for the second step, after staff have reviewed/corrected this."""
    platform_service.get_business_or_404(db, business_id)
    images = [(file.file.read(), file.content_type) for file in files]
    try:
        categories = menu_import_service.extract_menu_from_images(images)
    except menu_import_service.MenuImportNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return MenuImportExtractResponse(categories=categories)


@router.post("/publish", response_model=MenuImportPublishResponse)
def publish_menu(
    business_id: uuid.UUID,
    payload: MenuImportPublishRequest,
    db: Session = Depends(get_db),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    """Step 2 of 2: staff have reviewed/corrected the extracted draft
    (edited names, fixed misread prices, deleted anything wrong) and are
    now committing it as real menu categories/items for this business."""
    with transaction(db):
        platform_service.get_business_or_404(db, business_id)
        categories_created, items_created = menu_service.import_categories_and_items(
            db, business_id, payload.categories
        )
        audit_service.record(
            db, action="platform.menu_import_publish", business_id=business_id,
            platform_user_id=platform_user.id, resource_type="menu_category",
            metadata={"categories_created": categories_created, "items_created": items_created},
        )
    return MenuImportPublishResponse(categories_created=categories_created, items_created=items_created)
