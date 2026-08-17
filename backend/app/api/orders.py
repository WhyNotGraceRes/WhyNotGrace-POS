import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_feature, require_roles
from app.core.permissions import ROLE_BILLING, ROLE_OPERATIONAL, ROLE_SERVICE
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.enums import FeatureModule, OrderSource, OrderStatus
from app.schemas.order import OrderCreateRequest, OrderOut
from app.services import audit_service, order_service

router = APIRouter(prefix="/orders", tags=["orders"])

_STAFF_ORDER_ROLES = ROLE_BILLING | ROLE_SERVICE


@router.get("", response_model=list[OrderOut])
def list_orders(
    status_filter: OrderStatus | None = None,
    source: OrderSource | None = None,
    active_only: bool = False,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*_STAFF_ORDER_ROLES)),
):
    orders = order_service.list_orders(db, business_id, status_filter=status_filter, source=source, active_only=active_only)
    return [OrderOut.model_validate(o) for o in orders]


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*_STAFF_ORDER_ROLES)),
):
    return OrderOut.model_validate(order_service.get_order_or_404(db, business_id, order_id))


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreateRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*_STAFF_ORDER_ROLES)),
):
    with transaction(db):
        order = order_service.create_order(
            db,
            business_id=business_id,
            location_id=payload.location_id,
            source=payload.source,
            pricing_context=payload.pricing_context,
            items_payload=payload.items,
            customer_id=payload.customer_id,
            placed_by_staff_id=user.id,
            notes=payload.notes,
            delivery_address=payload.delivery_address,
            delivery_instructions=payload.delivery_instructions,
        )
        audit_service.record(
            db, action="order.create", business_id=business_id, user_id=user.id,
            resource_type="order", resource_id=str(order.id), metadata={"source": payload.source.value},
        )
    return OrderOut.model_validate(order)


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(
    order_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        order = order_service.cancel_order(db, business_id, order_id)
        audit_service.record(
            db, action="order.cancel", business_id=business_id, user_id=user.id,
            resource_type="order", resource_id=str(order_id),
        )
    return OrderOut.model_validate(order)
