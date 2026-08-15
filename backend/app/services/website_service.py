import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.enums import FeatureModule
from app.models.feature_flag import FeatureFlag
from app.models.website import WebsiteConfig


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
