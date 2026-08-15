import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_ANY_STAFF, ROLE_OPERATIONAL
from app.database.session import get_db
from app.database.transaction import transaction
from app.schemas.customer import CustomerCreate, CustomerOut, CustomerUpdate
from app.services import audit_service, customer_service

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerOut])
def list_customers(
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_ANY_STAFF)),
):
    return [CustomerOut.model_validate(c) for c in customer_service.list_customers(db, business_id)]


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_ANY_STAFF)),
):
    with transaction(db):
        customer = customer_service.get_or_create_by_mobile(db, business_id, payload)
        audit_service.record(
            db, action="customer.create", business_id=business_id, user_id=user.id,
            resource_type="customer", resource_id=str(customer.id),
        )
    return CustomerOut.model_validate(customer)


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerUpdate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        customer = customer_service.update_customer(db, business_id, customer_id, payload)
        audit_service.record(
            db, action="customer.update", business_id=business_id, user_id=user.id,
            resource_type="customer", resource_id=str(customer_id),
        )
    return CustomerOut.model_validate(customer)
