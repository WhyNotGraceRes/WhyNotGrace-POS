"""Real-time operational dashboard. Every figure is computed with a live
PostgreSQL query scoped to business_id — never hardcoded or cached client-side.
"""
import uuid
from datetime import datetime, time, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.billing import Bill
from app.models.customer import Customer
from app.models.enums import (
    BillStatus,
    KOTStatus,
    LocationStatus,
    LocationType,
    OrderSource,
    OrderStatus,
)
from app.models.kot import KOT
from app.models.location import Location
from app.models.loyalty import LoyaltyAccount
from app.models.menu import MenuItem
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.enums import PaymentStatus


def _today_start_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime.combine(now.date(), time.min, tzinfo=timezone.utc)


def build_dashboard(db: Session, business_id: uuid.UUID):
    today_start = _today_start_utc()

    orders_today = db.query(func.count(Order.id)).filter(
        Order.business_id == business_id, Order.created_at >= today_start
    ).scalar() or 0

    pending_orders = db.query(func.count(Order.id)).filter(
        Order.business_id == business_id,
        Order.status.notin_([OrderStatus.SERVED, OrderStatus.DELIVERED, OrderStatus.COMPLETED, OrderStatus.CANCELLED]),
    ).scalar() or 0

    kot_queue = db.query(func.count(KOT.id)).filter(
        KOT.business_id == business_id, KOT.status.in_([KOTStatus.NEW, KOTStatus.ACCEPTED, KOTStatus.PREPARING])
    ).scalar() or 0

    ready_orders = db.query(func.count(KOT.id)).filter(
        KOT.business_id == business_id, KOT.status == KOTStatus.READY
    ).scalar() or 0

    tables_total = db.query(func.count(Location.id)).filter(
        Location.business_id == business_id, Location.location_type == LocationType.TABLE, Location.is_active.is_(True)
    ).scalar() or 0
    tables_occupied = db.query(func.count(Location.id)).filter(
        Location.business_id == business_id, Location.location_type == LocationType.TABLE,
        Location.status != LocationStatus.AVAILABLE,
    ).scalar() or 0

    rooms_total = db.query(func.count(Location.id)).filter(
        Location.business_id == business_id, Location.location_type == LocationType.ROOM, Location.is_active.is_(True)
    ).scalar() or 0
    rooms_occupied = db.query(func.count(Location.id)).filter(
        Location.business_id == business_id, Location.location_type == LocationType.ROOM,
        Location.status != LocationStatus.AVAILABLE,
    ).scalar() or 0

    pending_bills = db.query(func.count(Bill.id)).filter(
        Bill.business_id == business_id, Bill.status.in_([BillStatus.OPEN, BillStatus.PARTIALLY_PAID])
    ).scalar() or 0

    payments_today_row = db.query(
        func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0)
    ).filter(
        Payment.business_id == business_id, Payment.status == PaymentStatus.SUCCESS,
        Payment.created_at >= today_start,
    ).first()
    payments_today_count = payments_today_row[0] or 0
    payments_today_amount = float(payments_today_row[1] or 0)

    top_items_rows = (
        db.query(OrderItem.menu_item_id, OrderItem.item_name_snapshot, func.sum(OrderItem.quantity).label("qty"))
        .join(Order, Order.id == OrderItem.order_id)
        .filter(OrderItem.business_id == business_id, Order.status != OrderStatus.CANCELLED)
        .group_by(OrderItem.menu_item_id, OrderItem.item_name_snapshot)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
        .all()
    )

    customer_count = db.query(func.count(Customer.id)).filter(Customer.business_id == business_id).scalar() or 0

    loyalty_accounts = db.query(func.count(LoyaltyAccount.id)).filter(
        LoyaltyAccount.business_id == business_id
    ).scalar() or 0
    loyalty_points = db.query(func.coalesce(func.sum(LoyaltyAccount.points_balance), 0)).filter(
        LoyaltyAccount.business_id == business_id
    ).scalar() or 0

    def _count_source_today(source: OrderSource) -> int:
        return db.query(func.count(Order.id)).filter(
            Order.business_id == business_id, Order.source == source, Order.created_at >= today_start
        ).scalar() or 0

    pickup_today = _count_source_today(OrderSource.PICKUP)
    delivery_today = _count_source_today(OrderSource.DELIVERY)

    return {
        "sales_today": payments_today_amount,
        "orders_today": orders_today,
        "pending_orders": pending_orders,
        "kot_queue": kot_queue,
        "ready_orders": ready_orders,
        "tables_occupied": tables_occupied,
        "tables_total": tables_total,
        "rooms_occupied": rooms_occupied,
        "rooms_total": rooms_total,
        "pending_bills": pending_bills,
        "payments_today_count": payments_today_count,
        "payments_today_amount": payments_today_amount,
        "top_menu_items": [
            {"menu_item_id": r[0], "name": r[1], "quantity_sold": int(r[2])} for r in top_items_rows
        ],
        "customer_count": customer_count,
        "loyalty_accounts": loyalty_accounts,
        "loyalty_points_outstanding": float(loyalty_points),
        "website_orders_today": pickup_today + delivery_today,
        "pickup_orders_today": pickup_today,
        "delivery_orders_today": delivery_today,
    }
