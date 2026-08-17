"""Central order engine. Every order — dine-in, QR, room service, pickup,
delivery, POS, or a future marketplace integration — is created through
create_order(). Prices are always resolved server-side via
pricing_service; the client only ever supplies item/variant/option ids.
"""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.ws_manager import manager as ws_manager
from app.models.billing import Bill
from app.models.enums import BillStatus, DeliveryStatus, KOTStatus, LocationStatus, LocationType, OrderSource, OrderStatus, PricingContext
from app.models.kot import KOT
from app.models.location import Location
from app.models.order import Order, OrderItem, OrderItemOption, OrderSession
from app.services import kot_service, notification_service, pricing_service
from app.utils.numbering import generate_number

# Default pricing context inferred from location type when the caller
# does not explicitly choose one (e.g. POS UI lets staff override).
_DEFAULT_CONTEXT_BY_LOCATION_TYPE = {
    LocationType.TABLE: PricingContext.DINE_IN,
    LocationType.ROOM: PricingContext.ROOM_SERVICE,
    LocationType.COUNTER: PricingContext.DINE_IN,
    LocationType.SECTION: PricingContext.DINE_IN,
    LocationType.OTHER: PricingContext.CUSTOM,
}

_SOURCES_WITHOUT_PERSISTENT_LOCATION = {OrderSource.PICKUP, OrderSource.DELIVERY}

# Every status an order can sit in before it's served/delivered/completed/
# cancelled — i.e. still somebody's job to move forward. Used by
# list_orders(active_only=True) so counter-facing screens can get a bounded
# "what's still open" count instead of pulling a business's entire order
# history.
_ACTIVE_ORDER_STATUSES = (
    OrderStatus.PLACED,
    OrderStatus.CONFIRMED,
    OrderStatus.PREPARING,
    OrderStatus.READY,
    OrderStatus.OUT_FOR_DELIVERY,
)


def _order_query(db: Session, business_id: uuid.UUID):
    return (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.options), joinedload(Order.customer))
        .filter(Order.business_id == business_id)
    )


def get_order_or_404(db: Session, business_id: uuid.UUID, order_id: uuid.UUID) -> Order:
    order = _order_query(db, business_id).filter(Order.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


def list_orders(
    db: Session,
    business_id: uuid.UUID,
    *,
    status_filter: OrderStatus | None = None,
    source: OrderSource | None = None,
    active_only: bool = False,
) -> list[Order]:
    query = _order_query(db, business_id)
    if status_filter:
        query = query.filter(Order.status == status_filter)
    elif active_only:
        query = query.filter(Order.status.in_(_ACTIVE_ORDER_STATUSES))
    if source:
        query = query.filter(Order.source == source)
    return query.order_by(Order.created_at.desc()).all()


def _get_or_create_session(
    db: Session, business_id: uuid.UUID, *, location_id: uuid.UUID | None, source: OrderSource, customer_id: uuid.UUID | None
) -> tuple[OrderSession, bool]:
    """Returns (session, is_additional). A location-bound session (table /
    room) stays open across multiple orders until the bill is paid. A
    pickup/delivery order always starts its own session.
    """
    if location_id is not None and source not in _SOURCES_WITHOUT_PERSISTENT_LOCATION:
        existing = (
            db.query(OrderSession)
            .filter(
                OrderSession.business_id == business_id,
                OrderSession.location_id == location_id,
                OrderSession.is_closed.is_(False),
            )
            .first()
        )
        if existing is not None:
            return existing, True

    session = OrderSession(
        business_id=business_id, location_id=location_id, customer_id=customer_id, source=source
    )
    db.add(session)
    db.flush()
    return session, False


def create_order(
    db: Session,
    *,
    business_id: uuid.UUID,
    location_id: uuid.UUID | None,
    source: OrderSource,
    pricing_context: PricingContext | None,
    items_payload: list,
    customer_id: uuid.UUID | None = None,
    placed_by_staff_id: uuid.UUID | None = None,
    notes: str | None = None,
    delivery_address: str | None = None,
    delivery_instructions: str | None = None,
    hold_kot: bool = False,
) -> Order:
    location: Location | None = None
    if location_id is not None:
        location = db.query(Location).filter(Location.id == location_id, Location.business_id == business_id).first()
        if location is None or not location.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid location")

    if pricing_context is None:
        pricing_context = (
            _DEFAULT_CONTEXT_BY_LOCATION_TYPE.get(location.location_type, PricingContext.CUSTOM)
            if location
            else (PricingContext.PICKUP if source == OrderSource.PICKUP else PricingContext.DELIVERY)
        )

    if source == OrderSource.DELIVERY and not delivery_address:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="delivery_address is required for delivery orders")

    session, is_additional = _get_or_create_session(
        db, business_id, location_id=location_id, source=source, customer_id=customer_id
    )

    order = Order(
        business_id=business_id,
        session_id=session.id,
        location_id=location_id,
        customer_id=customer_id,
        order_number=generate_number("ORD"),
        source=source,
        pricing_context=pricing_context,
        status=OrderStatus.PLACED,
        is_additional=is_additional,
        subtotal=0,
        notes=notes,
        placed_by_staff_id=placed_by_staff_id,
        delivery_status=DeliveryStatus.PLACED.value if source == OrderSource.DELIVERY else None,
        delivery_address=delivery_address,
        delivery_instructions=delivery_instructions,
    )
    db.add(order)
    db.flush()

    subtotal = 0.0
    for item_payload in items_payload:
        computed = pricing_service.compute_line_item(
            db,
            business_id=business_id,
            item_id=item_payload.menu_item_id,
            variant_id=item_payload.variant_id,
            option_ids=item_payload.option_ids,
            quantity=item_payload.quantity,
            context=pricing_context,
        )
        order_item = OrderItem(
            business_id=business_id,
            order_id=order.id,
            menu_item_id=computed["item"].id,
            variant_id=item_payload.variant_id,
            item_name_snapshot=computed["item"].name,
            quantity=item_payload.quantity,
            unit_price=computed["unit_price"],
            line_total=computed["line_total"],
            special_instructions=item_payload.special_instructions,
        )
        db.add(order_item)
        db.flush()

        for option in computed["options"]:
            db.add(
                OrderItemOption(
                    business_id=business_id,
                    order_item_id=order_item.id,
                    option_id=option.id,
                    option_name_snapshot=option.name,
                    price_delta_snapshot=float(option.price_delta),
                )
            )
        subtotal += computed["line_total"]

    order.subtotal = round(subtotal, 2)
    db.flush()

    if location is not None:
        location.status = LocationStatus.KITCHEN
        db.flush()

    if not hold_kot:
        kot_service.create_kot_for_order(db, order)

    # Only when a customer placed this themselves (QR/pickup/delivery/the
    # website) — a staff member placing an order at the counter doesn't
    # need to be told about the thing they just did.
    if placed_by_staff_id is None:
        notification_service.notify_new_customer_order(db, business_id, order)

    ws_manager.notify(business_id, "orders", "tables", "kot", "kitchen", "dashboard")
    return get_order_or_404(db, business_id, order.id)


def cancel_order(db: Session, business_id: uuid.UUID, order_id: uuid.UUID) -> Order:
    order = get_order_or_404(db, business_id, order_id)
    if order.status in (OrderStatus.SERVED, OrderStatus.DELIVERED, OrderStatus.COMPLETED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel a completed order")
    order.status = OrderStatus.CANCELLED
    db.flush()
    ws_manager.notify(business_id, "orders", "kot", "kitchen")
    return order


def _get_session_or_404(db: Session, business_id: uuid.UUID, session_id: uuid.UUID) -> OrderSession:
    session = (
        db.query(OrderSession)
        .filter(OrderSession.id == session_id, OrderSession.business_id == business_id)
        .first()
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


def _reject_if_billed(db: Session, business_id: uuid.UUID, session: OrderSession, location_name: str) -> None:
    """Both transfer and merge move orders between locations/sessions —
    something a Bill (whose own location_id and line items are a snapshot
    taken at generate time) has no way to follow. Simplest safe rule:
    once billing has started for a table, its floor position is frozen;
    settle or void the bill first."""
    has_bill = (
        db.query(Bill.id).filter(Bill.business_id == business_id, Bill.session_id == session.id).first()
        is not None
    )
    if has_bill:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{location_name} already has a bill started — settle or void it first",
        )


def transfer_session(
    db: Session, business_id: uuid.UUID, session_id: uuid.UUID, new_location_id: uuid.UUID
) -> OrderSession:
    """Moves an open table/room's entire running order (and every order in
    it) to a different, currently-available table/room — a guest asking to
    move seats, or two staff realizing a booking was set at the wrong table.
    """
    session = _get_session_or_404(db, business_id, session_id)
    if session.is_closed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This session is already closed")
    if session.location_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only dine-in/room sessions can be transferred"
        )
    if session.location_id == new_location_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already at that table")

    new_location = (
        db.query(Location).filter(Location.id == new_location_id, Location.business_id == business_id).first()
    )
    if new_location is None or not new_location.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid destination table")
    if new_location.status != LocationStatus.AVAILABLE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{new_location.name} is not available")

    old_location = db.query(Location).filter(Location.id == session.location_id).first()
    _reject_if_billed(db, business_id, session, old_location.name if old_location else "This table")

    # The new table inherits whatever occupancy state the old one was in
    # (ORDERING, KITCHEN, etc.) rather than resetting to a generic
    # OCCUPIED — a table mid-way through service stays mid-way through
    # service, just at a different physical spot.
    new_location.status = old_location.status if old_location else LocationStatus.OCCUPIED
    if old_location:
        old_location.status = LocationStatus.AVAILABLE

    session.location_id = new_location.id
    db.flush()

    orders = db.query(Order).filter(Order.session_id == session.id, Order.status != OrderStatus.CANCELLED).all()
    order_ids = [order.id for order in orders]
    for order in orders:
        order.location_id = new_location.id

    # A ticket already in the kitchen still needs to say where the food is
    # actually going — otherwise it gets carried to the table the guest
    # just left.
    if order_ids:
        db.query(KOT).filter(
            KOT.order_id.in_(order_ids), KOT.status.notin_([KOTStatus.SERVED, KOTStatus.CANCELLED])
        ).update({"location_id": new_location.id}, synchronize_session=False)

    db.flush()
    ws_manager.notify(business_id, "orders", "tables", "kot", "kitchen")
    return session


def merge_sessions(
    db: Session, business_id: uuid.UUID, from_session_id: uuid.UUID, into_session_id: uuid.UUID
) -> OrderSession:
    """Folds one open table's orders into another's — two tables pushed
    together for a bigger party who want a single bill. The losing
    table's session closes for real (unlike the reuse-forever session a
    table normally keeps — see docs/billing-counter-plan.md's "a settled
    table can be billed again": that gap is about a session outliving its
    own table's payment, not this, where the session is deliberately
    retired and can never receive another order again by construction)."""
    if from_session_id == into_session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot merge a table into itself")

    from_session = _get_session_or_404(db, business_id, from_session_id)
    into_session = _get_session_or_404(db, business_id, into_session_id)
    if from_session.is_closed or into_session.is_closed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One of these sessions is already closed")
    if from_session.location_id is None or into_session.location_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only dine-in/room sessions can be merged"
        )

    from_location = db.query(Location).filter(Location.id == from_session.location_id).first()
    into_location = db.query(Location).filter(Location.id == into_session.location_id).first()
    _reject_if_billed(db, business_id, from_session, from_location.name if from_location else "This table")
    _reject_if_billed(db, business_id, into_session, into_location.name if into_location else "This table")

    orders = db.query(Order).filter(Order.session_id == from_session.id, Order.status != OrderStatus.CANCELLED).all()
    order_ids = [order.id for order in orders]
    for order in orders:
        order.session_id = into_session.id
        order.location_id = into_session.location_id

    if order_ids:
        db.query(KOT).filter(
            KOT.order_id.in_(order_ids), KOT.status.notin_([KOTStatus.SERVED, KOTStatus.CANCELLED])
        ).update({"location_id": into_session.location_id}, synchronize_session=False)

    if from_location:
        from_location.status = LocationStatus.AVAILABLE

    from_session.is_closed = True
    from_session.closed_at = datetime.now(timezone.utc)
    db.flush()
    ws_manager.notify(business_id, "orders", "tables", "kot", "kitchen", "billing")
    return into_session


# Legal forward transitions for a delivery order's lifecycle. DELIVERED and
# CANCELLED are terminal — nothing may follow them. Cancellation is allowed
# from any non-terminal state (a customer/restaurant can call off a delivery
# any time before it's out the door — captured per-state below rather than
# universally, so DELIVERED can never regress to CANCELLED).
DELIVERY_STATUS_TRANSITIONS: dict[str, set[str]] = {
    DeliveryStatus.PLACED.value: {DeliveryStatus.CONFIRMED.value, DeliveryStatus.CANCELLED.value},
    DeliveryStatus.CONFIRMED.value: {DeliveryStatus.PREPARING.value, DeliveryStatus.CANCELLED.value},
    DeliveryStatus.PREPARING.value: {DeliveryStatus.READY.value, DeliveryStatus.CANCELLED.value},
    DeliveryStatus.READY.value: {DeliveryStatus.OUT_FOR_DELIVERY.value, DeliveryStatus.CANCELLED.value},
    DeliveryStatus.OUT_FOR_DELIVERY.value: {DeliveryStatus.DELIVERED.value, DeliveryStatus.CANCELLED.value},
    DeliveryStatus.DELIVERED.value: set(),
    DeliveryStatus.CANCELLED.value: set(),
}


def update_delivery_status(db: Session, business_id: uuid.UUID, order_id: uuid.UUID, new_status: str) -> Order:
    order = get_order_or_404(db, business_id, order_id)
    if order.source != OrderSource.DELIVERY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order is not a delivery order")

    current = order.delivery_status or DeliveryStatus.PLACED.value
    allowed = DELIVERY_STATUS_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition delivery status from {current} to {new_status}",
        )

    order.delivery_status = new_status
    # OrderStatus mirrors DeliveryStatus's values 1:1 for delivery orders,
    # so staff-facing order/kitchen views reflect live delivery progress
    # instead of only jumping once at final DELIVERED (the Phase 6 bug).
    order.status = OrderStatus(new_status)
    db.flush()
    ws_manager.notify(business_id, "orders", "delivery")
    return order
