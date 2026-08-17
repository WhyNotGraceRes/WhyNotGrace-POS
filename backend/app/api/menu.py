import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_OPERATIONAL
from app.database.session import get_db
from app.database.transaction import transaction
from app.schemas.menu import (
    MenuItemCreate,
    MenuItemOut,
    MenuItemUpdate,
    MenuOptionCreate,
    MenuOptionGroupCreate,
    MenuOptionGroupOut,
    MenuOptionGroupUpdate,
    MenuOptionOut,
    MenuOptionUpdate,
    MenuVariantCreate,
    MenuVariantOut,
    MenuVariantUpdate,
)
from app.schemas.translation import ItemTranslationUpdateRequest, TranslationOut
from app.services import audit_service, menu_service

router = APIRouter(prefix="/menu", tags=["menu"])


@router.get("/items", response_model=list[MenuItemOut])
def list_items(
    category_id: uuid.UUID | None = None,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    return [MenuItemOut.model_validate(i) for i in menu_service.list_items(db, business_id, category_id)]


@router.get("/items/{item_id}", response_model=MenuItemOut)
def get_item(item_id: uuid.UUID, business_id=Depends(get_current_business_id), db: Session = Depends(get_db)):
    return MenuItemOut.model_validate(menu_service.get_item_or_404(db, business_id, item_id))


@router.post("/items", response_model=MenuItemOut, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: MenuItemCreate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        item = menu_service.create_item(db, business_id, payload)
        audit_service.record(
            db, action="menu_item.create", business_id=business_id, user_id=user.id,
            resource_type="menu_item", resource_id=str(item.id),
        )
    return MenuItemOut.model_validate(item)


@router.put("/items/{item_id}", response_model=MenuItemOut)
def update_item(
    item_id: uuid.UUID,
    payload: MenuItemUpdate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        item = menu_service.update_item(db, business_id, item_id, payload)
        audit_service.record(
            db, action="menu_item.update", business_id=business_id, user_id=user.id,
            resource_type="menu_item", resource_id=str(item_id), metadata=payload.model_dump(exclude_unset=True),
        )
    return MenuItemOut.model_validate(item)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        menu_service.delete_item(db, business_id, item_id)
        audit_service.record(
            db, action="menu_item.delete", business_id=business_id, user_id=user.id,
            resource_type="menu_item", resource_id=str(item_id),
        )


@router.get("/items/{item_id}/translations", response_model=list[TranslationOut])
def get_item_translations(
    item_id: uuid.UUID, business_id=Depends(get_current_business_id), db: Session = Depends(get_db)
):
    return menu_service.list_item_translations(db, business_id, item_id)


@router.put("/items/{item_id}/translations/{language}", response_model=TranslationOut)
def set_item_translation(
    item_id: uuid.UUID,
    language: str,
    payload: ItemTranslationUpdateRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        result = menu_service.set_item_translation(db, business_id, item_id, language, payload)
        audit_service.record(
            db, action="menu_item.translation_update", business_id=business_id, user_id=user.id,
            resource_type="menu_item", resource_id=str(item_id), metadata={"language": language},
        )
    return result


@router.post("/items/{item_id}/variants", response_model=MenuItemOut, status_code=status.HTTP_201_CREATED)
def add_variant(
    item_id: uuid.UUID,
    payload: MenuVariantCreate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        item = menu_service.add_variant(db, business_id, item_id, payload)
    return MenuItemOut.model_validate(item)


@router.post("/items/{item_id}/option-groups", response_model=MenuItemOut, status_code=status.HTTP_201_CREATED)
def add_option_group(
    item_id: uuid.UUID,
    payload: MenuOptionGroupCreate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        item = menu_service.add_option_group(db, business_id, item_id, payload)
    return MenuItemOut.model_validate(item)


@router.post("/option-groups/{group_id}/options", response_model=MenuOptionOut, status_code=status.HTTP_201_CREATED)
def add_option(
    group_id: uuid.UUID,
    payload: MenuOptionCreate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        option = menu_service.add_option(db, business_id, group_id, payload)
    return MenuOptionOut.model_validate(option)


@router.put("/variants/{variant_id}", response_model=MenuVariantOut)
def update_variant(
    variant_id: uuid.UUID,
    payload: MenuVariantUpdate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        variant = menu_service.update_variant(db, business_id, variant_id, payload)
        audit_service.record(
            db, action="menu_variant.update", business_id=business_id, user_id=user.id,
            resource_type="menu_variant", resource_id=str(variant_id), metadata=payload.model_dump(exclude_unset=True),
        )
    return MenuVariantOut.model_validate(variant)


@router.delete("/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_variant(
    variant_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        menu_service.delete_variant(db, business_id, variant_id)
        audit_service.record(
            db, action="menu_variant.delete", business_id=business_id, user_id=user.id,
            resource_type="menu_variant", resource_id=str(variant_id),
        )


@router.put("/option-groups/{group_id}", response_model=MenuOptionGroupOut)
def update_option_group(
    group_id: uuid.UUID,
    payload: MenuOptionGroupUpdate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        group = menu_service.update_option_group(db, business_id, group_id, payload)
        audit_service.record(
            db, action="menu_option_group.update", business_id=business_id, user_id=user.id,
            resource_type="menu_option_group", resource_id=str(group_id), metadata=payload.model_dump(exclude_unset=True),
        )
    return MenuOptionGroupOut.model_validate(group)


@router.delete("/option-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_option_group(
    group_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        menu_service.delete_option_group(db, business_id, group_id)
        audit_service.record(
            db, action="menu_option_group.delete", business_id=business_id, user_id=user.id,
            resource_type="menu_option_group", resource_id=str(group_id),
        )


@router.put("/options/{option_id}", response_model=MenuOptionOut)
def update_option(
    option_id: uuid.UUID,
    payload: MenuOptionUpdate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        option = menu_service.update_option(db, business_id, option_id, payload)
        audit_service.record(
            db, action="menu_option.update", business_id=business_id, user_id=user.id,
            resource_type="menu_option", resource_id=str(option_id), metadata=payload.model_dump(exclude_unset=True),
        )
    return MenuOptionOut.model_validate(option)


@router.delete("/options/{option_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_option(
    option_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        menu_service.delete_option(db, business_id, option_id)
        audit_service.record(
            db, action="menu_option.delete", business_id=business_id, user_id=user.id,
            resource_type="menu_option", resource_id=str(option_id),
        )
