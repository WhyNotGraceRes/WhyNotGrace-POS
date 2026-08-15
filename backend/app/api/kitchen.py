"""Kitchen queue view (for kitchen displays) and the Service Counter
workflow (marking ready orders as served). Both operate on KOT records,
so they live alongside /kot rather than duplicating that model.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_KITCHEN, ROLE_SERVICE
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.enums import KOTStatus
from app.schemas.kot import KOTOut
from app.services import audit_service, kot_service

router = APIRouter(prefix="/kitchen", tags=["kitchen"])


@router.get("/queue", response_model=list[KOTOut])
def kitchen_queue(
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_KITCHEN)),
):
    """Pending + active KOTs, oldest first, for a kitchen display screen."""
    kots = kot_service.list_kots(
        db, business_id, statuses=[KOTStatus.NEW, KOTStatus.ACCEPTED, KOTStatus.PREPARING]
    )
    return [KOTOut.model_validate(k) for k in kots]


@router.get("/service/ready", response_model=list[KOTOut])
def ready_for_service(
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_SERVICE)),
):
    kots = kot_service.list_kots(db, business_id, statuses=[KOTStatus.READY])
    return [KOTOut.model_validate(k) for k in kots]


@router.post("/service/{kot_id}/serve", response_model=KOTOut)
def mark_served(
    kot_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_SERVICE)),
):
    with transaction(db):
        kot = kot_service.update_kot_status(db, business_id, kot_id, KOTStatus.SERVED)
        audit_service.record(
            db, action="kot.served", business_id=business_id, user_id=user.id,
            resource_type="kot", resource_id=str(kot_id),
        )
    return KOTOut.model_validate(kot)
