import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_FULL_ACCESS, ROLE_OPERATIONAL
from app.core.security import hash_password
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.staff import StaffCreateRequest, StaffOut, StaffUpdateRequest
from app.services import audit_service

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("", response_model=list[StaffOut])
def list_staff(
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    staff = db.query(User).filter(User.business_id == business_id).order_by(User.created_at).all()
    return [StaffOut.model_validate(s) for s in staff]


@router.post("", response_model=StaffOut, status_code=status.HTTP_201_CREATED)
def create_staff(
    payload: StaffCreateRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    if payload.role == UserRole.OWNER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot create a second OWNER via staff API")

    existing = db.query(User).filter(
        or_(User.email == payload.email.lower(), User.mobile == payload.mobile)
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or mobile already in use")

    with transaction(db):
        staff = User(
            business_id=business_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email.lower(),
            mobile=payload.mobile,
            password_hash=hash_password(payload.password),
            role=payload.role,
            is_active=True,
            is_email_verified=True,  # staff accounts are provisioned by the owner, no self-verification needed
        )
        db.add(staff)
        db.flush()
        audit_service.record(
            db, action="staff.create", business_id=business_id, user_id=user.id,
            resource_type="user", resource_id=str(staff.id), metadata={"role": payload.role.value},
        )
    return StaffOut.model_validate(staff)


def _get_staff_in_tenant(db: Session, business_id: uuid.UUID, staff_id: uuid.UUID) -> User:
    staff = db.query(User).filter(User.id == staff_id, User.business_id == business_id).first()
    if staff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")
    return staff


@router.put("/{staff_id}", response_model=StaffOut)
def update_staff(
    staff_id: uuid.UUID,
    payload: StaffUpdateRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    with transaction(db):
        staff = _get_staff_in_tenant(db, business_id, staff_id)
        if staff.role == UserRole.OWNER:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify the OWNER account here")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(staff, field, value)
        db.flush()
        audit_service.record(
            db, action="staff.update", business_id=business_id, user_id=user.id,
            resource_type="user", resource_id=str(staff.id),
        )
    return StaffOut.model_validate(staff)


@router.post("/{staff_id}/reset-access", response_model=StaffOut)
def reset_staff_access(
    staff_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    """Deactivate + reactivate account and revoke all active sessions —
    used when a device/staff credential is believed compromised.
    """
    from app.models.user import RefreshToken
    from datetime import datetime, timezone

    with transaction(db):
        staff = _get_staff_in_tenant(db, business_id, staff_id)
        db.query(RefreshToken).filter(
            RefreshToken.user_id == staff.id, RefreshToken.revoked_at.is_(None)
        ).update({"revoked_at": datetime.now(timezone.utc)})
        staff.failed_login_attempts = 0
        staff.locked_until = None
        db.flush()
        audit_service.record(
            db, action="staff.reset_access", business_id=business_id, user_id=user.id,
            resource_type="user", resource_id=str(staff.id),
        )
    return StaffOut.model_validate(staff)
