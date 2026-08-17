import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.business import Business
from app.models.enums import FeatureModule, PricingContext
from app.models.feature_flag import FeatureFlag
from app.models.menu import MenuCategory, MenuItem
from app.models.website import WebsiteConfig
from app.services import pricing_service
from app.utils.i18n import translate


def get_or_create_config(db: Session, business_id: uuid.UUID) -> WebsiteConfig:
    config = db.query(WebsiteConfig).filter(WebsiteConfig.business_id == business_id).first()
    if config is None:
        config = WebsiteConfig(business_id=business_id)
        db.add(config)
        db.flush()
    return config


def update_config(db: Session, business_id: uuid.UUID, payload) -> WebsiteConfig:
    config = get_or_create_config(db, business_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(config, field, value)
    db.flush()
    return config


def get_public_website(db: Session, business_slug: str):
    business = db.query(Business).filter(Business.slug == business_slug, Business.is_active.is_(True)).first()
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    website_flag = db.query(FeatureFlag).filter(
        FeatureFlag.business_id == business.id, FeatureFlag.module == FeatureModule.ONLINE_WEBSITE
    ).first()
    if website_flag is None or not website_flag.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not available for this business")

    config = get_or_create_config(db, business.id)
    if not config.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not published")

    def _flag_enabled(module: FeatureModule) -> bool:
        f = db.query(FeatureFlag).filter(FeatureFlag.business_id == business.id, FeatureFlag.module == module).first()
        return bool(f and f.enabled)

    return business, config, _flag_enabled(FeatureModule.PICKUP), _flag_enabled(FeatureModule.DELIVERY)


def get_public_menu(db: Session, business: Business, language: str = "en") -> list:
    """The website's menu section — same category/item shape the QR
    ordering flow uses (see qr_service.build_menu_response), but priced
    under PICKUP context since a website visitor isn't at any specific
    table/room. Not cached like the QR version: a marketing-site visit is
    far less frequent than a table's repeat menu fetches during service,
    so the cache's value here doesn't clear its complexity.
    """
    from app.schemas.qr import QRMenuCategoryOut, QRMenuItemOut, QRMenuOptionGroupOut, QRMenuOptionOut, QRMenuVariantOut

    categories = (
        db.query(MenuCategory)
        .options(
            joinedload(MenuCategory.items).joinedload(MenuItem.variants),
            joinedload(MenuCategory.items).joinedload(MenuItem.option_groups),
        )
        .filter(MenuCategory.business_id == business.id, MenuCategory.is_active.is_(True))
        .order_by(MenuCategory.display_order)
        .all()
    )

    all_active_items = [item for category in categories for item in category.items if item.is_active]
    unit_price_by_item_id = pricing_service.resolve_unit_prices_bulk(
        db, business_id=business.id, items=all_active_items, context=PricingContext.PICKUP
    )

    result = []
    for category in categories:
        items_out = []
        for item in sorted(category.items, key=lambda i: i.display_order):
            if not item.is_active or item.is_sold_out:
                continue
            items_out.append(
                QRMenuItemOut(
                    id=item.id,
                    name=translate(db, business.id, "menu_item", item.id, "name", language, item.name),
                    description=translate(
                        db, business.id, "menu_item", item.id, "description", language, item.description or ""
                    )
                    or None,
                    price=unit_price_by_item_id[item.id],
                    is_veg=item.is_veg,
                    is_sold_out=item.is_sold_out,
                    is_todays_special=item.is_todays_special,
                    is_specialty=item.is_specialty,
                    image_url=item.image_url,
                    variants=[
                        QRMenuVariantOut(id=v.id, name=v.name, price_delta=float(v.price_delta), is_default=v.is_default)
                        for v in item.variants if v.is_active
                    ],
                    option_groups=[
                        QRMenuOptionGroupOut(
                            id=g.id, name=g.name, is_required=g.is_required, allow_multiple=g.allow_multiple,
                            options=[
                                QRMenuOptionOut(id=o.id, name=o.name, price_delta=float(o.price_delta))
                                for o in g.options if o.is_active
                            ],
                        )
                        for g in item.option_groups
                    ],
                )
            )
        if items_out:
            result.append(
                QRMenuCategoryOut(
                    id=category.id,
                    name=translate(db, business.id, "menu_category", category.id, "name", language, category.name),
                    items=items_out,
                )
            )
    return result
