"""Business provisioning by WhyNotGrace's own staff — the replacement for
open self-registration (app.api.auth no longer has a /register route). The
resulting owner account is created active and pre-verified, matching the
same "created active, no self-verification" precedent app/api/staff.py
already sets for staff provisioned by a business owner.
"""
import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.business import Business, BusinessSettings
from app.models.enums import ALWAYS_ON_FEATURES, FeatureModule, UserRole
from app.models.feature_flag import FeatureFlag
from app.models.user import User
from app.services import audit_service
from app.utils.slugify import unique_slug


def provision_business(db: Session, payload, platform_user_id: uuid.UUID) -> User:
    existing = db.query(User).filter(
        or_(User.email == payload.owner_email.lower(), User.mobile == payload.owner_mobile)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email or mobile number already exists",
        )

    slug = unique_slug(db, Business, payload.business_name)

    business = Business(name=payload.business_name, slug=slug, business_type=payload.business_type)
    db.add(business)
    db.flush()

    db.add(BusinessSettings(business_id=business.id))

    for module in FeatureModule:
        db.add(
            FeatureFlag(
                business_id=business.id,
                module=module,
                enabled=module in ALWAYS_ON_FEATURES,
            )
        )

    owner = User(
        business_id=business.id,
        first_name=payload.owner_first_name,
        last_name=payload.owner_last_name,
        email=payload.owner_email.lower(),
        mobile=payload.owner_mobile,
        password_hash=hash_password(payload.owner_password),
        role=UserRole.OWNER,
        is_active=True,
        is_email_verified=True,
    )
    db.add(owner)
    db.flush()

    audit_service.record(
        db, action="platform.business_provisioned", business_id=business.id, platform_user_id=platform_user_id,
        resource_type="business", resource_id=str(business.id),
        metadata={"business_name": business.name, "owner_email": owner.email},
    )

    return owner


def list_businesses(db: Session) -> list[Business]:
    return db.query(Business).order_by(Business.created_at.desc()).all()


def get_business_or_404(db: Session, business_id: uuid.UUID) -> Business:
    business = db.get(Business, business_id)
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return business


def set_business_active(db: Session, business_id: uuid.UUID, *, is_active: bool, platform_user_id: uuid.UUID) -> Business:
    """The manual kill-switch — immediate, no grace period. Distinct from
    the billing-driven grace/suspend lifecycle in subscription_service:
    this is for fraud/abuse/support decisions, not a lapsed payment.
    """
    business = get_business_or_404(db, business_id)
    business.is_active = is_active
    db.flush()
    audit_service.record(
        db, action="platform.business_active_changed", business_id=business.id, platform_user_id=platform_user_id,
        resource_type="business", resource_id=str(business.id), metadata={"is_active": is_active},
    )
    return business
