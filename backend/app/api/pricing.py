import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_OPERATIONAL
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.pricing import PriceRule
from app.schemas.pricing import PriceRuleCreate, PriceRuleOut, PriceRuleUpdate
from app.services import audit_service, menu_service

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.get("/rules", response_model=list[PriceRuleOut])
def list_rules(
    item_id: uuid.UUID | None = None,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
):
    query = db.query(PriceRule).filter(PriceRule.business_id == business_id)
    if item_id:
        query = query.filter(PriceRule.item_id == item_id)
    return [PriceRuleOut.model_validate(r) for r in query.all()]


@router.post("/rules", response_model=PriceRuleOut, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: PriceRuleCreate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    menu_service.get_item_or_404(db, business_id, payload.item_id)
    with transaction(db):
        rule = PriceRule(business_id=business_id, **payload.model_dump())
        db.add(rule)
        db.flush()
        audit_service.record(
            db, action="price_rule.create", business_id=business_id, user_id=user.id,
            resource_type="price_rule", resource_id=str(rule.id),
        )
    return PriceRuleOut.model_validate(rule)


@router.put("/rules/{rule_id}", response_model=PriceRuleOut)
def update_rule(
    rule_id: uuid.UUID,
    payload: PriceRuleUpdate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        rule = db.query(PriceRule).filter(PriceRule.id == rule_id, PriceRule.business_id == business_id).first()
        if rule is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Price rule not found")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(rule, field, value)
        db.flush()
        audit_service.record(
            db, action="price_rule.update", business_id=business_id, user_id=user.id,
            resource_type="price_rule", resource_id=str(rule_id),
        )
    return PriceRuleOut.model_validate(rule)


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        rule = db.query(PriceRule).filter(PriceRule.id == rule_id, PriceRule.business_id == business_id).first()
        if rule is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Price rule not found")
        db.delete(rule)
        db.flush()
        audit_service.record(
            db, action="price_rule.delete", business_id=business_id, user_id=user.id,
            resource_type="price_rule", resource_id=str(rule_id),
        )
