from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_OPERATIONAL
from app.database.session import get_db
from app.services import reports_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/sales")
def sales(
    granularity: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    return reports_service.sales_report(db, business_id, granularity=granularity, start_date=start_date, end_date=end_date)


@router.get("/orders")
def orders(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    return reports_service.order_count_report(db, business_id, start_date=start_date, end_date=end_date)


@router.get("/payments")
def payments(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    return reports_service.payment_breakdown_report(db, business_id, start_date=start_date, end_date=end_date)


@router.get("/top-items")
def top_items(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 10,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    return reports_service.top_items_report(db, business_id, start_date=start_date, end_date=end_date, limit=limit)


@router.get("/categories")
def categories(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    return reports_service.category_performance_report(db, business_id, start_date=start_date, end_date=end_date)


@router.get("/channels")
def channels(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    return reports_service.channel_performance_report(db, business_id, start_date=start_date, end_date=end_date)
