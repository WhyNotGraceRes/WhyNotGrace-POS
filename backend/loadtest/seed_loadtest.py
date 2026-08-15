"""LOAD-TEST-ONLY seed script. Run against the isolated `whynotgrace_loadtest`
database — NEVER against a dev or production database.

Creates:
  - Business A ("LoadTest Grand Hotel"): a realistic-sized menu (6 categories
    x 6 items, with variants/option-groups on some items) and 50 tables, each
    with a real QRCode row — this is the business the staged load test hits.
  - Business B ("LoadTest Isolation Control"): a small, separate business
    used only to verify tenant isolation during/after the load test (its
    data must never appear in Business A's responses, and vice versa).

Also pre-provisions up to `--sessions` real QRSession rows per business
directly via the same QRSession model the app's own `/qr/scan` endpoint
writes to (not a separate code path, not a new endpoint) and writes them to
JSONL files that the locustfile reads. This is done directly against the DB,
bypassing the HTTP `/qr/scan` call, specifically because `/qr/scan` is
rate-limited to 30/min per source IP (see app/core/rate_limit.py) — since a
Locust load generator originates from a single machine/IP, provisioning
thousands of sessions *through* that endpoint would take hours and would
only be testing the rate limiter, not the app. The load test itself still
exercises every other QR endpoint (menu load, order placement, order-status
polling) over real HTTP against the real running application. This mirrors
reality anyway: a real customer scans once, then the sustained load is menu
browsing / ordering / status polling, not repeated scanning.

Usage (from backend/, with the venv active):
    DATABASE_URL=postgresql+psycopg://whynotgrace:changeme_dev_password@localhost:5544/whynotgrace_loadtest \
        python -m loadtest.seed_loadtest --sessions 5000

Refuses to run when APP_ENV=production or when DATABASE_URL does not contain
"loadtest", as a guard against accidentally pointing this at a real database.
"""
import argparse
import json
import sys
from pathlib import Path

from app.core.config import get_settings
from app.core.security import generate_url_safe_token, hash_password
from app.database.session import SessionLocal
from app.models.business import Business, BusinessSettings
from app.models.enums import ALWAYS_ON_FEATURES, BusinessType, FeatureModule, LocationType, UserRole
from app.models.feature_flag import FeatureFlag
from app.models.location import Location, QRCode
from app.models.location import QRSession
from app.models.menu import MenuCategory, MenuItem, MenuOption, MenuOptionGroup, MenuVariant
from app.models.user import User
from app.utils.slugify import unique_slug
from datetime import datetime, timedelta, timezone

SEED_PASSWORD = "LoadTestDevPassword123!"
OUT_DIR = Path(__file__).parent / "data"

CATEGORY_ITEMS = {
    "Starters": ["Paneer Tikka", "Veg Spring Rolls", "Chicken 65", "Hara Bhara Kebab", "Fish Fingers", "Corn Cheese Balls"],
    "Soups": ["Tomato Basil Soup", "Sweet Corn Soup", "Hot & Sour Soup", "Manchow Soup", "Cream of Mushroom", "Lemon Coriander Soup"],
    "Main Course": ["Butter Chicken", "Paneer Butter Masala", "Dal Makhani", "Veg Kolhapuri", "Chicken Biryani", "Mutton Rogan Josh"],
    "Breads": ["Butter Naan", "Garlic Naan", "Tandoori Roti", "Laccha Paratha", "Missi Roti", "Cheese Naan"],
    "Desserts": ["Gulab Jamun", "Rasmalai", "Chocolate Brownie", "Kulfi", "Gajar Halwa", "Ice Cream Sundae"],
    "Beverages": ["Masala Chai", "Fresh Lime Soda", "Mango Lassi", "Cold Coffee", "Mineral Water", "Buttermilk"],
}


def _seed_menu(db, business_id):
    item_refs = []
    for order, (cat_name, item_names) in enumerate(CATEGORY_ITEMS.items(), start=1):
        category = MenuCategory(business_id=business_id, name=cat_name, display_order=order)
        db.add(category)
        db.flush()
        for i, item_name in enumerate(item_names):
            item = MenuItem(
                business_id=business_id, category_id=category.id, name=item_name,
                base_price=99 + (i * 30) + (order * 10), is_veg=(i % 3 != 1), display_order=i,
            )
            db.add(item)
            db.flush()
            # Every third item gets a size variant.
            if i % 3 == 0:
                db.add(MenuVariant(business_id=business_id, item_id=item.id, name="Half", price_delta=-40, is_default=False))
                db.add(MenuVariant(business_id=business_id, item_id=item.id, name="Full", price_delta=0, is_default=True))
            # Every other item gets an option group (spice level).
            if i % 2 == 0:
                group = MenuOptionGroup(business_id=business_id, item_id=item.id, name="Spice Level", is_required=False, allow_multiple=False)
                db.add(group)
                db.flush()
                for opt_name, delta in [("Mild", 0), ("Medium", 0), ("Extra Spicy", 10)]:
                    db.add(MenuOption(business_id=business_id, group_id=group.id, name=opt_name, price_delta=delta))
            item_refs.append({"id": str(item.id), "name": item.name, "base_price": float(item.base_price)})
    db.flush()
    return item_refs


def _seed_business(db, *, name: str, table_count: int, owner_email: str, owner_mobile: str):
    existing = db.query(Business).filter(Business.name == name).first()
    if existing:
        print(f"[skip] {name} already exists (id={existing.id}) — delete it manually first if you want a clean reseed")
        return None

    slug = unique_slug(db, Business, name)
    business = Business(name=name, slug=slug, business_type=BusinessType.HOTEL)
    db.add(business)
    db.flush()

    db.add(BusinessSettings(business_id=business.id, default_tax_percent=5, default_service_charge_percent=5))

    for module in FeatureModule:
        db.add(FeatureFlag(business_id=business.id, module=module, enabled=module in ALWAYS_ON_FEATURES or module == FeatureModule.QR_ORDERING))

    owner = User(
        business_id=business.id, first_name="LoadTest", last_name="Owner", email=owner_email, mobile=owner_mobile,
        password_hash=hash_password(SEED_PASSWORD), role=UserRole.OWNER, is_active=True, is_email_verified=True,
    )
    db.add(owner)
    db.flush()

    item_refs = _seed_menu(db, business.id)

    tables = []
    for i in range(1, table_count + 1):
        table = Location(business_id=business.id, location_type=LocationType.TABLE, name=f"T{i}", capacity=4)
        db.add(table)
        db.flush()
        code = generate_url_safe_token(16)
        db.add(QRCode(business_id=business.id, location_id=table.id, code=code))
        tables.append({"location_id": str(table.id), "name": table.name, "code": code})

    db.flush()
    db.commit()
    print(f"[created] {name} slug={slug} id={business.id} tables={table_count} items={len(item_refs)}")
    return {"business": business, "slug": slug, "tables": tables, "items": item_refs}


def _provision_sessions(db, business_id, tables, count, hours_valid):
    """Directly insert QRSession rows (same model/table `/qr/scan` writes to)
    round-robined across the given tables, bypassing the rate-limited HTTP
    scan endpoint for bulk test-data setup. See module docstring."""
    sessions = []
    expires_at = datetime.now(timezone.utc) + timedelta(hours=hours_valid)
    for i in range(count):
        table = tables[i % len(tables)]
        token = generate_url_safe_token()
        db.add(QRSession(business_id=business_id, location_id=table["location_id"], session_token=token, expires_at=expires_at))
        sessions.append({"session_token": token, "location_id": table["location_id"], "table_name": table["name"]})
        if (i + 1) % 500 == 0:
            db.flush()
            print(f"  ...provisioned {i + 1}/{count} sessions")
    db.flush()
    db.commit()
    return sessions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sessions", type=int, default=5000, help="QR sessions to pre-provision for Business A")
    parser.add_argument("--isolation-sessions", type=int, default=50, help="QR sessions to pre-provision for Business B (isolation control)")
    parser.add_argument("--tables", type=int, default=50, help="Number of tables for Business A")
    parser.add_argument("--session-hours", type=int, default=48, help="Hours the pre-provisioned sessions stay valid")
    args = parser.parse_args()

    settings = get_settings()
    if settings.is_production:
        print("Refusing to seed: APP_ENV=production.", file=sys.stderr)
        sys.exit(1)
    if "loadtest" not in settings.database_url:
        print(f"Refusing to seed: DATABASE_URL does not look like the load-test database: {settings.database_url}", file=sys.stderr)
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        biz_a = _seed_business(db, name="LoadTest Grand Hotel", table_count=args.tables, owner_email="loadtest-owner-a@example.com", owner_mobile="9100000001")
        biz_b = _seed_business(db, name="LoadTest Isolation Control", table_count=3, owner_email="loadtest-owner-b@example.com", owner_mobile="9100000002")

        if biz_a is not None:
            print(f"Provisioning {args.sessions} QR sessions for Business A...")
            sessions_a = _provision_sessions(db, biz_a["business"].id, biz_a["tables"], args.sessions, args.session_hours)
            (OUT_DIR / "sessions_business_a.jsonl").write_text("\n".join(json.dumps(s) for s in sessions_a), encoding="utf-8")
            (OUT_DIR / "business_a_meta.json").write_text(json.dumps({
                "business_id": str(biz_a["business"].id), "slug": biz_a["slug"], "items": biz_a["items"], "tables": biz_a["tables"],
            }, indent=2), encoding="utf-8")

        if biz_b is not None:
            print(f"Provisioning {args.isolation_sessions} QR sessions for Business B (isolation control)...")
            sessions_b = _provision_sessions(db, biz_b["business"].id, biz_b["tables"], args.isolation_sessions, args.session_hours)
            (OUT_DIR / "sessions_business_b.jsonl").write_text("\n".join(json.dumps(s) for s in sessions_b), encoding="utf-8")
            (OUT_DIR / "business_b_meta.json").write_text(json.dumps({
                "business_id": str(biz_b["business"].id), "slug": biz_b["slug"], "items": biz_b["items"], "tables": biz_b["tables"],
            }, indent=2), encoding="utf-8")
    finally:
        db.close()

    print(f"\nSeed complete. Session files + metadata written to {OUT_DIR}")


if __name__ == "__main__":
    main()
