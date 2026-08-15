import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core import cache
from app.core.config import get_settings
from app.core.dependencies import require_feature_for_business
from app.core.security import generate_url_safe_token
from app.models.business import Business
from app.models.enums import FeatureModule, LocationType, PricingContext
from app.models.location import Location, QRCode, QRSession
from app.models.menu import MenuCategory, MenuItem
from app.services import pricing_service
from app.utils.i18n import translate

settings = get_settings()

_CONTEXT_BY_LOCATION_TYPE = {
    LocationType.TABLE: PricingContext.DINE_IN,
    LocationType.ROOM: PricingContext.ROOM_SERVICE,
    LocationType.COUNTER: PricingContext.DINE_IN,
    LocationType.SECTION: PricingContext.DINE_IN,
    LocationType.OTHER: PricingContext.CUSTOM,
}


def get_business_by_slug_or_404(db: Session, slug: str) -> Business:
    business = db.query(Business).filter(Business.slug == slug, Business.is_active.is_(True)).first()
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return business


def start_session(db: Session, *, business_slug: str, location_id: uuid.UUID, code: str) -> tuple[QRSession, Business, Location]:
    business = get_business_by_slug_or_404(db, business_slug)
    require_feature_for_business(db, business.id, FeatureModule.QR_ORDERING)

    location = db.query(Location).filter(
        Location.id == location_id, Location.business_id == business.id, Location.is_active.is_(True)
    ).first()
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")

    qr = db.query(QRCode).filter(QRCode.location_id == location.id, QRCode.is_active.is_(True)).first()
    if qr is None or qr.code != code:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid QR code")

    session = QRSession(
        business_id=business.id,
        location_id=location.id,
        session_token=generate_url_safe_token(),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.qr_session_expire_hours),
    )
    db.add(session)
    db.flush()
    return session, business, location


def get_active_session_or_404(db: Session, session_token: str) -> QRSession:
    session = db.query(QRSession).filter(QRSession.session_token == session_token).first()
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired QR session")
    now = datetime.now(timezone.utc)
    if session.closed_at is not None or session.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="QR session has expired, please rescan")
    return session


def build_menu_response(db: Session, business: Business, location: Location, language: str = "en"):
    context = _CONTEXT_BY_LOCATION_TYPE.get(location.location_type, PricingContext.CUSTOM)

    from app.schemas.qr import (
        QRMenuCategoryOut,
        QRMenuItemOut,
        QRMenuOptionGroupOut,
        QRMenuOptionOut,
        QRMenuResponse,
        QRMenuVariantOut,
    )

    # Only the category/item list is cached — it depends solely on
    # business_id + location TYPE + language, never on which specific
    # table/room the guest is at (unlike location_name below, which does
    # and is therefore always read fresh from the caller's already-loaded
    # `location` object, never cached).
    cache_key = cache.menu_cache_key(business.id, location.location_type.value, language)
    cached = cache.get_json(cache_key)
    if cached is not None:
        category_out = [QRMenuCategoryOut.model_validate(c) for c in cached]
    else:
        categories = (
            db.query(MenuCategory)
            .options(joinedload(MenuCategory.items).joinedload(MenuItem.variants), joinedload(MenuCategory.items).joinedload(MenuItem.option_groups))
            .filter(MenuCategory.business_id == business.id, MenuCategory.is_active.is_(True))
            .order_by(MenuCategory.display_order)
            .all()
        )

        all_active_items = [item for category in categories for item in category.items if item.is_active]
        unit_price_by_item_id = pricing_service.resolve_unit_prices_bulk(
            db, business_id=business.id, items=all_active_items, context=context
        )

        category_out = []
        for category in categories:
            items_out = []
            for item in sorted(category.items, key=lambda i: i.display_order):
                if not item.is_active:
                    continue
                unit_price = unit_price_by_item_id[item.id]
                items_out.append(
                    QRMenuItemOut(
                        id=item.id,
                        name=translate(db, business.id, "menu_item", item.id, "name", language, item.name),
                        description=translate(db, business.id, "menu_item", item.id, "description", language, item.description or "") or None,
                        price=unit_price,
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
            category_out.append(
                QRMenuCategoryOut(
                    id=category.id,
                    name=translate(db, business.id, "menu_category", category.id, "name", language, category.name),
                    items=items_out,
                )
            )
        cache.set_json(cache_key, [c.model_dump(mode="json") for c in category_out])

    return QRMenuResponse(
        business_name=business.name, location_name=location.name, pricing_context=context.value, categories=category_out
    )
