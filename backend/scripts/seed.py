"""DEVELOPMENT-ONLY seed script.

Creates two real, isolated businesses (Business A and Business B) directly
in PostgreSQL via the normal SQLAlchemy models — no authentication bypass,
no mock data layer. Useful for manually exercising tenant isolation and
the QR/menu/order flow end to end.

Usage (from backend/, with the venv active and DATABASE_URL pointed at a
real, migrated Postgres database):

    python -m scripts.seed

Refuses to run when APP_ENV=production.
"""
import sys

from app.core.config import get_settings
from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.business import Business, BusinessSettings
from app.models.enums import ALWAYS_ON_FEATURES, BusinessType, FeatureModule, LocationType, UserRole
from app.models.feature_flag import FeatureFlag
from app.models.location import Location, QRCode
from app.models.menu import MenuCategory, MenuItem
from app.models.user import User
from app.utils.slugify import unique_slug
from app.core.security import generate_url_safe_token

SEED_PASSWORD = "DevPassword123!"


def _seed_business(db, *, name: str, business_type: BusinessType, owner_email: str, owner_mobile: str, enabled_modules: set[FeatureModule]):
    existing = db.query(Business).filter(Business.name == name).first()
    if existing:
        print(f"[skip] {name} already exists (id={existing.id})")
        return existing

    slug = unique_slug(db, Business, name)
    business = Business(name=name, slug=slug, business_type=business_type)
    db.add(business)
    db.flush()

    db.add(BusinessSettings(business_id=business.id, default_tax_percent=5, default_service_charge_percent=5))

    for module in FeatureModule:
        db.add(
            FeatureFlag(
                business_id=business.id, module=module,
                enabled=module in ALWAYS_ON_FEATURES or module in enabled_modules,
            )
        )

    owner = User(
        business_id=business.id, first_name="Dev", last_name="Owner", email=owner_email, mobile=owner_mobile,
        password_hash=hash_password(SEED_PASSWORD), role=UserRole.OWNER, is_active=True, is_email_verified=True,
    )
    db.add(owner)
    db.flush()

    category = MenuCategory(business_id=business.id, name="Starters", display_order=1)
    db.add(category)
    db.flush()

    item = MenuItem(
        business_id=business.id, category_id=category.id, name="Paneer Tikka", base_price=250,
        is_veg=True, is_todays_special=True,
    )
    db.add(item)
    db.flush()

    table = Location(business_id=business.id, location_type=LocationType.TABLE, name="T1", capacity=4)
    db.add(table)
    db.flush()
    db.add(QRCode(business_id=business.id, location_id=table.id, code=generate_url_safe_token(16)))

    db.flush()
    db.commit()
    print(f"[created] {name} slug={slug} owner={owner_email} password={SEED_PASSWORD}")
    return business


def main() -> None:
    settings = get_settings()
    if settings.is_production:
        print("Refusing to seed: APP_ENV=production.", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        _seed_business(
            db, name="Business A - The Spice Route", business_type=BusinessType.RESTAURANT,
            owner_email="owner-a@example.com", owner_mobile="9000000001",
            enabled_modules={FeatureModule.QR_ORDERING, FeatureModule.PICKUP, FeatureModule.DELIVERY, FeatureModule.LOYALTY, FeatureModule.REVIEWS},
        )
        _seed_business(
            db, name="Business B - Grace Hotel & Resort", business_type=BusinessType.HOTEL,
            owner_email="owner-b@example.com", owner_mobile="9000000002",
            enabled_modules={FeatureModule.HOTEL_ROOMS, FeatureModule.ROOM_SERVICE, FeatureModule.QR_ORDERING},
        )
    finally:
        db.close()

    print("\nSeed complete. These are DEVELOPMENT-ONLY credentials — do not use in production.")
    print(f"  owner-a@example.com / {SEED_PASSWORD}")
    print(f"  owner-b@example.com / {SEED_PASSWORD}")


if __name__ == "__main__":
    main()
