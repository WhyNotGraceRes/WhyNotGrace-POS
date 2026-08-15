import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_feature, require_roles
from app.core.permissions import ROLE_FULL_ACCESS, ROLE_OPERATIONAL
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.enums import FeatureModule
from app.models.loyalty import LoyaltyAccount, LoyaltyRule, Reward
from app.schemas.loyalty import (
    LoyaltyAccountOut,
    LoyaltyRuleCreate,
    LoyaltyRuleOut,
    LoyaltyRuleUpdate,
    RedeemRewardRequest,
    RewardOut,
)
from app.services import audit_service, loyalty_service

router = APIRouter(prefix="/loyalty", tags=["loyalty"], dependencies=[Depends(require_feature(FeatureModule.LOYALTY))])


@router.get("/rules", response_model=list[LoyaltyRuleOut])
def list_rules(
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    rules = db.query(LoyaltyRule).filter(LoyaltyRule.business_id == business_id).all()
    return [LoyaltyRuleOut.model_validate(r) for r in rules]


@router.post("/rules", response_model=LoyaltyRuleOut, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: LoyaltyRuleCreate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    with transaction(db):
        rule = LoyaltyRule(business_id=business_id, **payload.model_dump())
        db.add(rule)
        db.flush()
        audit_service.record(
            db, action="loyalty_rule.create", business_id=business_id, user_id=user.id,
            resource_type="loyalty_rule", resource_id=str(rule.id),
        )
    return LoyaltyRuleOut.model_validate(rule)


@router.put("/rules/{rule_id}", response_model=LoyaltyRuleOut)
def update_rule(
    rule_id: uuid.UUID,
    payload: LoyaltyRuleUpdate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    with transaction(db):
        rule = db.query(LoyaltyRule).filter(LoyaltyRule.id == rule_id, LoyaltyRule.business_id == business_id).first()
        if rule is None:
            from fastapi import HTTPException, status as http_status
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Loyalty rule not found")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(rule, field, value)
        db.flush()
        audit_service.record(
            db, action="loyalty_rule.update", business_id=business_id, user_id=user.id,
            resource_type="loyalty_rule", resource_id=str(rule_id),
        )
    return LoyaltyRuleOut.model_validate(rule)


@router.get("/accounts/{customer_id}", response_model=LoyaltyAccountOut)
def get_account(
    customer_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    account = db.query(LoyaltyAccount).filter(
        LoyaltyAccount.business_id == business_id, LoyaltyAccount.customer_id == customer_id
    ).first()
    if account is None:
        from fastapi import HTTPException, status as http_status
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="No loyalty account for this customer yet")
    return LoyaltyAccountOut.model_validate(account)


@router.get("/accounts/{customer_id}/rewards", response_model=list[RewardOut])
def list_rewards(
    customer_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    account = db.query(LoyaltyAccount).filter(
        LoyaltyAccount.business_id == business_id, LoyaltyAccount.customer_id == customer_id
    ).first()
    if account is None:
        return []
    rewards = db.query(Reward).filter(Reward.account_id == account.id).all()
    return [RewardOut.model_validate(r) for r in rewards]


@router.post("/rewards/{reward_id}/redeem", response_model=RewardOut)
def redeem_reward(
    reward_id: uuid.UUID,
    payload: RedeemRewardRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_OPERATIONAL)),
):
    with transaction(db):
        reward = loyalty_service.redeem_reward(db, business_id, reward_id, payload.order_id, user.id)
        audit_service.record(
            db, action="loyalty_reward.redeem", business_id=business_id, user_id=user.id,
            resource_type="reward", resource_id=str(reward_id),
        )
    return RewardOut.model_validate(reward)
