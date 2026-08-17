import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_ANY_STAFF
from app.database.session import get_db
from app.database.transaction import transaction
from app.schemas.notification import NotificationListOut
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListOut)
def list_notifications(
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_ANY_STAFF)),
):
    return notification_service.list_for_business(db, business_id)


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(
    notification_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_ANY_STAFF)),
):
    with transaction(db):
        notification_service.mark_read(db, business_id, notification_id)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_ANY_STAFF)),
):
    with transaction(db):
        notification_service.mark_all_read(db, business_id)
