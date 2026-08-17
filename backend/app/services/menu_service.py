import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.menu import MenuCategory, MenuItem, MenuOption, MenuOptionGroup, MenuVariant


def _delete_or_409(db: Session, entity, *, in_use_detail: str) -> None:
    """Delete a menu entity, translating the DB's RESTRICT constraint
    (raised when the entity is referenced by a historical order item or
    option) into a clean 409 instead of a raw IntegrityError. Historical
    orders must never be corrupted by a menu edit, so the row is kept.
    """
    db.delete(entity)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=in_use_detail) from exc


def _get_category_or_404(db: Session, business_id: uuid.UUID, category_id: uuid.UUID) -> MenuCategory:
    category = db.query(MenuCategory).filter(
        MenuCategory.id == category_id, MenuCategory.business_id == business_id
    ).first()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


def list_categories(db: Session, business_id: uuid.UUID) -> list[MenuCategory]:
    return (
        db.query(MenuCategory)
        .filter(MenuCategory.business_id == business_id)
        .order_by(MenuCategory.display_order, MenuCategory.name)
        .all()
    )


def create_category(db: Session, business_id: uuid.UUID, payload) -> MenuCategory:
    category = MenuCategory(business_id=business_id, **payload.model_dump())
    db.add(category)
    db.flush()
    return category


def update_category(db: Session, business_id: uuid.UUID, category_id: uuid.UUID, payload) -> MenuCategory:
    category = _get_category_or_404(db, business_id, category_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.flush()
    return category


def delete_category(db: Session, business_id: uuid.UUID, category_id: uuid.UUID) -> None:
    category = _get_category_or_404(db, business_id, category_id)
    db.delete(category)
    db.flush()


def _item_query(db: Session, business_id: uuid.UUID):
    return (
        db.query(MenuItem)
        .options(
            joinedload(MenuItem.variants),
            joinedload(MenuItem.option_groups).joinedload(MenuOptionGroup.options),
        )
        .filter(MenuItem.business_id == business_id)
    )


def get_item_or_404(db: Session, business_id: uuid.UUID, item_id: uuid.UUID) -> MenuItem:
    item = _item_query(db, business_id).filter(MenuItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
    return item


def list_items(db: Session, business_id: uuid.UUID, category_id: uuid.UUID | None = None) -> list[MenuItem]:
    query = _item_query(db, business_id)
    if category_id:
        query = query.filter(MenuItem.category_id == category_id)
    return query.order_by(MenuItem.display_order, MenuItem.name).all()


def create_item(db: Session, business_id: uuid.UUID, payload) -> MenuItem:
    _get_category_or_404(db, business_id, payload.category_id)

    data = payload.model_dump(exclude={"variants", "option_groups"})
    item = MenuItem(business_id=business_id, **data)
    db.add(item)
    db.flush()

    for variant_payload in payload.variants:
        db.add(MenuVariant(business_id=business_id, item_id=item.id, **variant_payload.model_dump()))

    for group_payload in payload.option_groups:
        group_data = group_payload.model_dump(exclude={"options"})
        group = MenuOptionGroup(business_id=business_id, item_id=item.id, **group_data)
        db.add(group)
        db.flush()
        for option_payload in group_payload.options:
            db.add(MenuOption(business_id=business_id, group_id=group.id, **option_payload.model_dump()))

    db.flush()
    return get_item_or_404(db, business_id, item.id)


def update_item(db: Session, business_id: uuid.UUID, item_id: uuid.UUID, payload) -> MenuItem:
    item = get_item_or_404(db, business_id, item_id)
    data = payload.model_dump(exclude_unset=True)
    if "category_id" in data and data["category_id"] is not None:
        _get_category_or_404(db, business_id, data["category_id"])
    # Restocking un-86's the item automatically — an owner who just typed
    # in a fresh count clearly means for it to be orderable again, and
    # making them separately remember to flip is_sold_out back is exactly
    # the kind of two-step chore this field exists to remove. Only when
    # the same request doesn't also set is_sold_out explicitly, so a
    # deliberate "restock but keep it hidden" call is still respected.
    if data.get("stock_quantity") is not None and data["stock_quantity"] > 0 and "is_sold_out" not in data:
        data["is_sold_out"] = False
    for field, value in data.items():
        setattr(item, field, value)
    db.flush()
    return get_item_or_404(db, business_id, item.id)


def delete_item(db: Session, business_id: uuid.UUID, item_id: uuid.UUID) -> None:
    item = get_item_or_404(db, business_id, item_id)
    db.delete(item)
    db.flush()


def add_variant(db: Session, business_id: uuid.UUID, item_id: uuid.UUID, payload) -> MenuItem:
    get_item_or_404(db, business_id, item_id)
    db.add(MenuVariant(business_id=business_id, item_id=item_id, **payload.model_dump()))
    db.flush()
    return get_item_or_404(db, business_id, item_id)


def get_variant_or_404(db: Session, business_id: uuid.UUID, variant_id: uuid.UUID) -> MenuVariant:
    variant = db.query(MenuVariant).filter(
        MenuVariant.id == variant_id, MenuVariant.business_id == business_id
    ).first()
    if variant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")
    return variant


def update_variant(db: Session, business_id: uuid.UUID, variant_id: uuid.UUID, payload) -> MenuVariant:
    variant = get_variant_or_404(db, business_id, variant_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(variant, field, value)
    db.flush()
    return variant


def delete_variant(db: Session, business_id: uuid.UUID, variant_id: uuid.UUID) -> None:
    variant = get_variant_or_404(db, business_id, variant_id)
    _delete_or_409(
        db, variant,
        in_use_detail="Cannot delete this variant: it is used by existing orders. Deactivate it instead.",
    )


def add_option_group(db: Session, business_id: uuid.UUID, item_id: uuid.UUID, payload) -> MenuItem:
    get_item_or_404(db, business_id, item_id)
    group_data = payload.model_dump(exclude={"options"})
    group = MenuOptionGroup(business_id=business_id, item_id=item_id, **group_data)
    db.add(group)
    db.flush()
    for option_payload in payload.options:
        db.add(MenuOption(business_id=business_id, group_id=group.id, **option_payload.model_dump()))
    db.flush()
    return get_item_or_404(db, business_id, item_id)


def get_option_group_or_404(db: Session, business_id: uuid.UUID, group_id: uuid.UUID) -> MenuOptionGroup:
    group = db.query(MenuOptionGroup).filter(
        MenuOptionGroup.id == group_id, MenuOptionGroup.business_id == business_id
    ).first()
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option group not found")
    return group


def update_option_group(db: Session, business_id: uuid.UUID, group_id: uuid.UUID, payload) -> MenuOptionGroup:
    group = get_option_group_or_404(db, business_id, group_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(group, field, value)
    db.flush()
    return group


def delete_option_group(db: Session, business_id: uuid.UUID, group_id: uuid.UUID) -> None:
    group = get_option_group_or_404(db, business_id, group_id)
    _delete_or_409(
        db, group,
        in_use_detail="Cannot delete this option group: one or more of its options are used by existing orders. Deactivate it instead.",
    )


def add_option(db: Session, business_id: uuid.UUID, group_id: uuid.UUID, payload) -> MenuOption:
    group = get_option_group_or_404(db, business_id, group_id)
    option = MenuOption(business_id=business_id, group_id=group.id, **payload.model_dump())
    db.add(option)
    db.flush()
    return option


def get_option_or_404(db: Session, business_id: uuid.UUID, option_id: uuid.UUID) -> MenuOption:
    option = db.query(MenuOption).filter(
        MenuOption.id == option_id, MenuOption.business_id == business_id
    ).first()
    if option is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found")
    return option


def update_option(db: Session, business_id: uuid.UUID, option_id: uuid.UUID, payload) -> MenuOption:
    option = get_option_or_404(db, business_id, option_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(option, field, value)
    db.flush()
    return option


def delete_option(db: Session, business_id: uuid.UUID, option_id: uuid.UUID) -> None:
    option = get_option_or_404(db, business_id, option_id)
    _delete_or_409(
        db, option,
        in_use_detail="Cannot delete this option: it is used by existing orders. Deactivate it instead.",
    )
