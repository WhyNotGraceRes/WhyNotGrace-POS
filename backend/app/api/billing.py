import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_BILLING, ROLE_OPERATIONAL
from app.database.session import get_db
from app.database.transaction import transaction
from app.schemas.billing import ApplyDiscountRequest, BillOut, GenerateBillRequest
from app.services import audit_service, billing_service

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/generate", response_model=BillOut, status_code=status.HTTP_201_CREATED)
def generate_bill(
    payload: GenerateBillRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_BILLING)),
):
    with transaction(db):
        bill = billing_service.generate_or_refresh_bill(db, business_id, payload)
        audit_service.record(
            db, action="bill.generate", business_id=business_id, user_id=user.id,
            resource_type="bill", resource_id=str(bill.id),
        )
    return BillOut.model_validate(bill)


@router.get("/{bill_id}", response_model=BillOut)
def get_bill(
    bill_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_BILLING)),
):
    return BillOut.model_validate(billing_service.get_bill_or_404(db, business_id, bill_id))


@router.post("/{bill_id}/discount", response_model=BillOut)
def apply_discount(
    bill_id: uuid.UUID,
    payload: ApplyDiscountRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        bill = billing_service.apply_discount(db, business_id, bill_id, payload, user.id)
        audit_service.record(
            db, action="bill.discount_applied", business_id=business_id, user_id=user.id,
            resource_type="bill", resource_id=str(bill_id), metadata={"name": payload.name},
        )
    return BillOut.model_validate(bill)
