import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.ws_manager import manager as ws_manager
from app.models.enums import KOTStatus, OrderStatus
from app.models.kot import KOT, KOTItem
from app.models.order import Order
from app.utils.numbering import generate_number

# KOT lifecycle -> corresponding Order-level status.
_KOT_TO_ORDER_STATUS = {
    KOTStatus.NEW: OrderStatus.PLACED,
    KOTStatus.ACCEPTED: OrderStatus.CONFIRMED,
    KOTStatus.PREPARING: OrderStatus.PREPARING,
    KOTStatus.READY: OrderStatus.READY,
    KOTStatus.SERVED: OrderStatus.SERVED,
    KOTStatus.CANCELLED: OrderStatus.CANCELLED,
}

_ALLOWED_TRANSITIONS = {
    KOTStatus.NEW: {KOTStatus.ACCEPTED, KOTStatus.CANCELLED},
    KOTStatus.ACCEPTED: {KOTStatus.PREPARING, KOTStatus.CANCELLED},
    KOTStatus.PREPARING: {KOTStatus.READY, KOTStatus.CANCELLED},
    KOTStatus.READY: {KOTStatus.SERVED},
    KOTStatus.SERVED: set(),
    KOTStatus.CANCELLED: set(),
}


def create_kot_for_order(db: Session, order: Order) -> KOT:
    """Generate exactly one KOT covering the items of a single Order. Since
    each additional order is its own Order row, this naturally ensures
    only newly-added items are ever sent to the kitchen. An order whose
    items span multiple kitchen stations still gets one KOT — see
    app.services.receipt.builder for where that gets split into a
    per-station printed ticket.
    """
    kot = KOT(
        business_id=order.business_id,
        order_id=order.id,
        location_id=order.location_id,
        kot_number=generate_number("KOT"),
        status=KOTStatus.NEW,
        special_instructions=order.notes,
    )
    db.add(kot)
    db.flush()

    for item in order.items:
        options_summary = ", ".join(o.option_name_snapshot for o in item.options) or None
        db.add(
            KOTItem(
                business_id=order.business_id,
                kot_id=kot.id,
                order_item_id=item.id,
                item_name_snapshot=item.item_name_snapshot,
                quantity=item.quantity,
                options_summary=options_summary,
            )
        )
    db.flush()
    return kot


def has_kot(db: Session, order_id: uuid.UUID) -> bool:
    return db.query(KOT).filter(KOT.order_id == order_id).first() is not None


def release_held_kots_for_session(db: Session, business_id: uuid.UUID, session_id: uuid.UUID) -> None:
    """Fire KOTs for any order in this session that was created with
    hold_kot=True (pickup/delivery orders awaiting online payment
    confirmation) and doesn't have one yet. Called once a bill for the
    session is fully paid.
    """
    orders = (
        db.query(Order)
        .filter(Order.business_id == business_id, Order.session_id == session_id, Order.status != OrderStatus.CANCELLED)
        .all()
    )
    for order in orders:
        if not has_kot(db, order.id):
            create_kot_for_order(db, order)


def _kot_query(db: Session, business_id: uuid.UUID):
    return (
        db.query(KOT)
        .options(joinedload(KOT.items))
        .filter(KOT.business_id == business_id)
    )


def get_kot_or_404(db: Session, business_id: uuid.UUID, kot_id: uuid.UUID) -> KOT:
    kot = _kot_query(db, business_id).filter(KOT.id == kot_id).first()
    if kot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KOT not found")
    return kot


def list_kots(db: Session, business_id: uuid.UUID, statuses: list[KOTStatus] | None = None) -> list[KOT]:
    query = _kot_query(db, business_id)
    if statuses:
        query = query.filter(KOT.status.in_(statuses))
    return query.order_by(KOT.created_at).all()


def update_kot_status(db: Session, business_id: uuid.UUID, kot_id: uuid.UUID, new_status: KOTStatus, estimated_minutes: int | None = None) -> KOT:
    kot = get_kot_or_404(db, business_id, kot_id)
    allowed = _ALLOWED_TRANSITIONS.get(kot.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition KOT from {kot.status.value} to {new_status.value}",
        )
    kot.status = new_status
    if estimated_minutes is not None:
        kot.estimated_minutes = estimated_minutes
    db.flush()

    order = db.get(Order, kot.order_id)
    if order is not None:
        order.status = _KOT_TO_ORDER_STATUS[new_status]
        db.flush()

    ws_manager.notify(business_id, "kot", "kitchen", "orders")
    return kot
