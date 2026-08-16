import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_BILLING, ROLE_OPERATIONAL
from app.database.session import get_db
from app.database.transaction import transaction
from app.schemas.billing import (
    ApplyDiscountRequest,
    BillOut,
    BillPrintOut,
    GenerateBillRequest,
    VoidBillItemRequest,
    VoidBillRequest,
)
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


@router.post("/{bill_id}/void", response_model=BillOut)
def void_bill(
    bill_id: uuid.UUID,
    payload: VoidBillRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_BILLING)),
):
    """Cancels a bill without deleting it.

    Deliberately allowed for ROLE_BILLING at the router, with the tighter
    manager-only rule applied inside the service according to the
    billing.void_requires_manager toggle. Putting it in the router instead
    would make the toggle unable to loosen it, which is the point of having
    the toggle.
    """
    with transaction(db):
        bill = billing_service.void_bill(db, business_id, bill_id, reason=payload.reason, user=user)
        audit_service.record(
            db, action="bill.void", business_id=business_id, user_id=user.id,
            resource_type="bill", resource_id=str(bill.id),
            metadata={"reason": bill.void_reason, "invoice_number": bill.invoice_number},
        )
    return BillOut.model_validate(bill)


@router.post("/{bill_id}/items/{item_id}/void", response_model=BillOut)
def void_bill_item(
    bill_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: VoidBillItemRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_BILLING)),
):
    """Strikes a single line off an open bill.

    Router-level role matches the whole-bill void for the same reason given
    there: the tighter manager-only rule belongs in the service, where the
    billing.void_requires_manager toggle can reach it.
    """
    with transaction(db):
        bill = billing_service.void_bill_item(
            db, business_id, bill_id, item_id, reason=payload.reason, user=user
        )
        item = next((i for i in bill.items if i.id == item_id), None)
        audit_service.record(
            db, action="bill.item_void", business_id=business_id, user_id=user.id,
            resource_type="bill", resource_id=str(bill_id),
            metadata={
                "bill_item_id": str(item_id),
                "item_name": item.item_name_snapshot if item else None,
                "line_total": float(item.line_total) if item else None,
                "reason": item.void_reason if item else None,
            },
        )
    return BillOut.model_validate(bill)


@router.post("/{bill_id}/print", response_model=BillPrintOut)
def register_print(
    bill_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_BILLING)),
):
    """Records that the bill was printed and says whether this copy is a
    duplicate. Called by the client immediately before it renders, so the
    count reflects paper actually produced rather than screens opened."""
    with transaction(db):
        bill, is_duplicate = billing_service.register_print(db, business_id, bill_id)
        audit_service.record(
            db, action="bill.print", business_id=business_id, user_id=user.id,
            resource_type="bill", resource_id=str(bill.id),
            metadata={"print_count": bill.print_count, "duplicate": is_duplicate},
        )
    return BillPrintOut(
        bill=BillOut.model_validate(bill),
        is_duplicate=is_duplicate,
        print_count=bill.print_count,
    )
