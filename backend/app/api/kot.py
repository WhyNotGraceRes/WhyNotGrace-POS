import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_KITCHEN
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.enums import KOTStatus
from app.schemas.kot import KOTOut, KOTStatusUpdateRequest
from app.services import audit_service, kot_service

router = APIRouter(prefix="/kot", tags=["kot"])


@router.get("", response_model=list[KOTOut])
def list_kots(
    status_filter: KOTStatus | None = None,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_KITCHEN)),
):
    statuses = [status_filter] if status_filter else None
    return [KOTOut.model_validate(k) for k in kot_service.list_kots(db, business_id, statuses)]


@router.get("/{kot_id}", response_model=KOTOut)
def get_kot(
    kot_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_KITCHEN)),
):
    return KOTOut.model_validate(kot_service.get_kot_or_404(db, business_id, kot_id))


@router.put("/{kot_id}/status", response_model=KOTOut)
def update_kot_status(
    kot_id: uuid.UUID,
    payload: KOTStatusUpdateRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_KITCHEN)),
):
    with transaction(db):
        kot = kot_service.update_kot_status(db, business_id, kot_id, payload.status, payload.estimated_minutes)
        audit_service.record(
            db, action="kot.status_update", business_id=business_id, user_id=user.id,
            resource_type="kot", resource_id=str(kot_id), metadata={"status": payload.status.value},
        )
    return KOTOut.model_validate(kot)
