"""In-app notifications. Two kinds, deliberately handled differently:

- Persisted rows (Notification) for things that happen at one moment in
  time — right now, only "a customer placed an order without a staff
  member's involvement" (QR ordering, pickup/delivery checkout, the
  website). These can be read/unread and stick around until read.
- A synthetic "tickets are aging" notice, computed fresh on every list
  call rather than stored. There's no single moment a KOT "becomes
  stuck" — it's a continuous fact that's true or false depending on the
  clock — so storing it would mean either a background job to create and
  retire it (infra this app doesn't have) or a stale row lying about
  whether it's still true. Recomputing it is free and always correct.
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.ws_manager import manager as ws_manager
from app.models.enums import KOTStatus
from app.models.kot import KOT
from app.models.notification import Notification
from app.models.order import Order

STUCK_KOT_MINUTES = 20
_STUCK_KOT_SYNTHETIC_ID = "stuck-kots"


def create(
    db: Session,
    business_id: uuid.UUID,
    *,
    type: str,
    title: str,
    body: str | None = None,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
) -> Notification:
    notification = Notification(
        business_id=business_id, type=type, title=title, body=body,
        resource_type=resource_type, resource_id=resource_id,
    )
    db.add(notification)
    db.flush()
    ws_manager.notify(business_id, "notifications")
    return notification


def notify_new_customer_order(db: Session, business_id: uuid.UUID, order: Order) -> Notification:
    """Called only when placed_by_staff_id is None — a customer placed this
    themselves (QR/pickup/delivery/website), not a staff member at the
    counter. A staff-placed order doesn't need to alert the staff who just
    placed it."""
    source_label = order.source.value.replace("_", " ").title()
    return create(
        db, business_id,
        type="NEW_CUSTOMER_ORDER",
        title=f"New {source_label.lower()} order",
        body=f"Order {order.order_number}",
        resource_type="order",
        resource_id=order.id,
    )


def _stuck_kot_notice(db: Session, business_id: uuid.UUID) -> dict | None:
    threshold = datetime.now(timezone.utc) - timedelta(minutes=STUCK_KOT_MINUTES)
    stuck = (
        db.query(KOT)
        .filter(
            KOT.business_id == business_id,
            KOT.status.in_([KOTStatus.NEW, KOTStatus.ACCEPTED, KOTStatus.PREPARING]),
            KOT.created_at < threshold,
        )
        .order_by(KOT.created_at.asc())
        .all()
    )
    if not stuck:
        return None
    oldest_minutes = int((datetime.now(timezone.utc) - stuck[0].created_at).total_seconds() // 60)
    count = len(stuck)
    return {
        "id": _STUCK_KOT_SYNTHETIC_ID,
        "type": "STUCK_KOT",
        "title": "Tickets waiting a while" if count > 1 else "A ticket's been waiting a while",
        "body": (
            f"{count} tickets have been in the kitchen queue over {STUCK_KOT_MINUTES} minutes "
            f"(oldest: {oldest_minutes}m)"
            if count > 1
            else f"{oldest_minutes}m in the kitchen queue"
        ),
        "resource_type": "kot",
        "resource_id": stuck[0].id,
        "is_read": False,
        "created_at": stuck[0].created_at,
    }


def list_for_business(db: Session, business_id: uuid.UUID, *, limit: int = 50) -> dict:
    rows = (
        db.query(Notification)
        .filter(Notification.business_id == business_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )
    notifications = [
        {
            "id": str(n.id), "type": n.type, "title": n.title, "body": n.body,
            "resource_type": n.resource_type, "resource_id": n.resource_id,
            "is_read": n.is_read, "created_at": n.created_at,
        }
        for n in rows
    ]
    unread_count = sum(1 for n in notifications if not n["is_read"])

    stuck = _stuck_kot_notice(db, business_id)
    if stuck:
        notifications.insert(0, stuck)
        unread_count += 1

    return {"notifications": notifications, "unread_count": unread_count}


def mark_read(db: Session, business_id: uuid.UUID, notification_id: uuid.UUID) -> None:
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.business_id == business_id)
        .first()
    )
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        db.flush()


def mark_all_read(db: Session, business_id: uuid.UUID) -> None:
    now = datetime.now(timezone.utc)
    (
        db.query(Notification)
        .filter(Notification.business_id == business_id, Notification.is_read.is_(False))
        .update({"is_read": True, "read_at": now}, synchronize_session=False)
    )
    db.flush()
