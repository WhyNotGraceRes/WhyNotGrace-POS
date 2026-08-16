"""Reporting queries — all real PostgreSQL aggregations scoped to
business_id, no hardcoded figures.
"""
import uuid
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.billing import Bill
from app.models.business import BusinessSettings
from app.models.enums import OrderStatus, PaymentStatus
from app.models.menu import MenuCategory, MenuItem
from app.models.order import Order, OrderItem
from app.models.payment import Payment

DEFAULT_TIMEZONE = "Asia/Kolkata"
DEFAULT_RANGE_DAYS = 30


def _business_tz(db: Session, business_id: uuid.UUID) -> ZoneInfo:
    tz_name = (
        db.query(BusinessSettings.timezone)
        .filter(BusinessSettings.business_id == business_id)
        .scalar()
    )
    try:
        return ZoneInfo(tz_name or DEFAULT_TIMEZONE)
    except Exception:  # noqa: BLE001 - a bad timezone must not stop a report loading
        return ZoneInfo(DEFAULT_TIMEZONE)


def _resolve_range(db: Session, business_id: uuid.UUID, start_date, end_date):
    """Turn the API's calendar dates into a half-open range of UTC instants.

    Both bounds arrive as dates, not instants. The upper bound becomes the
    first moment of the *following* day and is compared with `<`, so the final
    day of a range is counted in full — comparing `created_at <= end_date`
    against a date parsed to midnight silently dropped it, which is why a range
    ending today reported nothing for today.

    The days are the restaurant's own days, taken from BusinessSettings, so a
    bill settled at 00:30 falls on the date its receipt shows rather than on
    the previous UTC one.
    """
    tz = _business_tz(db, business_id)
    if end_date is None:
        end_date = datetime.now(tz).date()
    if start_date is None:
        start_date = end_date - timedelta(days=DEFAULT_RANGE_DAYS)

    start = datetime.combine(start_date, time.min, tzinfo=tz)
    end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=tz)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def sales_report(db: Session, business_id: uuid.UUID, *, granularity: str, start_date=None, end_date=None):
    start, end = _resolve_range(db, business_id, start_date, end_date)
    trunc = {"daily": "day", "weekly": "week", "monthly": "month"}.get(granularity, "day")

    rows = (
        db.query(
            func.date_trunc(trunc, Payment.created_at).label("bucket"),
            func.coalesce(func.sum(Payment.amount), 0),
            func.count(func.distinct(Payment.bill_id)),
        )
        .filter(
            Payment.business_id == business_id, Payment.status == PaymentStatus.SUCCESS,
            Payment.created_at >= start, Payment.created_at < end,
        )
        .group_by("bucket")
        .order_by("bucket")
        .all()
    )
    return [{"period": r[0].isoformat(), "total_sales": float(r[1]), "bills_paid": r[2]} for r in rows]


def order_count_report(db: Session, business_id: uuid.UUID, *, start_date=None, end_date=None):
    start, end = _resolve_range(db, business_id, start_date, end_date)
    rows = (
        db.query(Order.source, func.count(Order.id))
        .filter(
            Order.business_id == business_id, Order.created_at >= start, Order.created_at < end,
            Order.status != OrderStatus.CANCELLED,
        )
        .group_by(Order.source)
        .all()
    )
    return [{"source": r[0].value, "order_count": r[1]} for r in rows]


def payment_breakdown_report(db: Session, business_id: uuid.UUID, *, start_date=None, end_date=None):
    start, end = _resolve_range(db, business_id, start_date, end_date)
    rows = (
        db.query(Payment.method, func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.business_id == business_id, Payment.status == PaymentStatus.SUCCESS,
            Payment.created_at >= start, Payment.created_at < end,
        )
        .group_by(Payment.method)
        .all()
    )
    return [{"method": r[0].value, "count": r[1], "total_amount": float(r[2])} for r in rows]


def top_items_report(db: Session, business_id: uuid.UUID, *, start_date=None, end_date=None, limit: int = 10):
    start, end = _resolve_range(db, business_id, start_date, end_date)
    rows = (
        db.query(OrderItem.menu_item_id, OrderItem.item_name_snapshot, func.sum(OrderItem.quantity), func.sum(OrderItem.line_total))
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            OrderItem.business_id == business_id, Order.status != OrderStatus.CANCELLED,
            Order.created_at >= start, Order.created_at < end,
        )
        .group_by(OrderItem.menu_item_id, OrderItem.item_name_snapshot)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
        .all()
    )
    return [
        {"menu_item_id": r[0], "name": r[1], "quantity_sold": int(r[2]), "revenue": float(r[3])} for r in rows
    ]


def category_performance_report(db: Session, business_id: uuid.UUID, *, start_date=None, end_date=None):
    start, end = _resolve_range(db, business_id, start_date, end_date)
    rows = (
        db.query(MenuCategory.id, MenuCategory.name, func.sum(OrderItem.line_total))
        .join(MenuItem, MenuItem.category_id == MenuCategory.id)
        .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            MenuCategory.business_id == business_id, Order.status != OrderStatus.CANCELLED,
            Order.created_at >= start, Order.created_at < end,
        )
        .group_by(MenuCategory.id, MenuCategory.name)
        .order_by(func.sum(OrderItem.line_total).desc())
        .all()
    )
    return [{"category_id": r[0], "category_name": r[1], "revenue": float(r[2])} for r in rows]


def channel_performance_report(db: Session, business_id: uuid.UUID, *, start_date=None, end_date=None):
    start, end = _resolve_range(db, business_id, start_date, end_date)
    rows = (
        db.query(Order.source, func.count(Order.id), func.coalesce(func.sum(Order.subtotal), 0))
        .filter(
            Order.business_id == business_id, Order.created_at >= start, Order.created_at < end,
            Order.status != OrderStatus.CANCELLED,
        )
        .group_by(Order.source)
        .all()
    )
    return [{"channel": r[0].value, "order_count": r[1], "revenue": float(r[2])} for r in rows]
