import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_OPERATIONAL
from app.database.session import get_db
from app.database.transaction import transaction
from app.schemas.menu import MenuCategoryCreate, MenuCategoryOut, MenuCategoryUpdate
from app.services import audit_service, menu_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[MenuCategoryOut])
def list_categories(business_id=Depends(get_current_business_id), db: Session = Depends(get_db)):
    return [MenuCategoryOut.model_validate(c) for c in menu_service.list_categories(db, business_id)]


@router.post("", response_model=MenuCategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: MenuCategoryCreate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        category = menu_service.create_category(db, business_id, payload)
        audit_service.record(
            db, action="menu_category.create", business_id=business_id, user_id=user.id,
            resource_type="menu_category", resource_id=str(category.id),
        )
    return MenuCategoryOut.model_validate(category)


@router.put("/{category_id}", response_model=MenuCategoryOut)
def update_category(
    category_id: uuid.UUID,
    payload: MenuCategoryUpdate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        category = menu_service.update_category(db, business_id, category_id, payload)
        audit_service.record(
            db, action="menu_category.update", business_id=business_id, user_id=user.id,
            resource_type="menu_category", resource_id=str(category_id),
        )
    return MenuCategoryOut.model_validate(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        menu_service.delete_category(db, business_id, category_id)
        audit_service.record(
            db, action="menu_category.delete", business_id=business_id, user_id=user.id,
            resource_type="menu_category", resource_id=str(category_id),
        )
