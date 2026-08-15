"""Configurable loyalty engine. Nothing is hardcoded — owners define
LoyaltyRule rows (see app.models.loyalty.RuleType) and this module fires
Rewards / points whenever a bill is fully paid for a known customer.
"""
import math
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.billing import Bill
from app.models.loyalty import LoyaltyAccount, LoyaltyRule, LoyaltyTransaction, Redemption, Reward, RuleType
from app.models.order import OrderSession


def _get_or_create_account(db: Session, business_id: uuid.UUID, customer_id: uuid.UUID) -> LoyaltyAccount:
    account = db.query(LoyaltyAccount).filter(
        LoyaltyAccount.business_id == business_id, LoyaltyAccount.customer_id == customer_id
    ).first()
    if account is None:
        account = LoyaltyAccount(business_id=business_id, customer_id=customer_id)
        db.add(account)
        db.flush()
    return account


def process_paid_bill(db: Session, business_id: uuid.UUID, bill: Bill) -> None:
    """Called after a bill transitions to PAID. Updates the customer's
    loyalty account and evaluates every active rule.
    """
    session = db.get(OrderSession, bill.session_id)
    if session is None or session.customer_id is None:
        return  # No known customer (e.g. anonymous dine-in) — nothing to accrue.

    account = _get_or_create_account(db, business_id, session.customer_id)
    account.total_orders += 1
    account.total_spend = float(account.total_spend) + float(bill.grand_total)
    db.flush()

    rules = db.query(LoyaltyRule).filter(LoyaltyRule.business_id == business_id, LoyaltyRule.is_active.is_(True)).all()
    for rule in rules:
        _evaluate_rule(db, business_id, account, rule)


def _reward_count_for_rule(db: Session, account_id: uuid.UUID, rule_id: uuid.UUID) -> int:
    return db.query(Reward).filter(Reward.account_id == account_id, Reward.rule_id == rule_id).count()


def _evaluate_rule(db: Session, business_id: uuid.UUID, account: LoyaltyAccount, rule: LoyaltyRule) -> None:
    if rule.rule_type == RuleType.ORDER_COUNT_THRESHOLD:
        if rule.threshold <= 0:
            return
        earned = int(account.total_orders // rule.threshold)
        already_given = _reward_count_for_rule(db, account.id, rule.id)
        for _ in range(earned - already_given):
            db.add(
                Reward(
                    business_id=business_id, account_id=account.id, rule_id=rule.id,
                    reward_type=rule.reward_type, reward_value=rule.reward_value,
                )
            )

    elif rule.rule_type == RuleType.SPEND_THRESHOLD:
        if rule.threshold <= 0:
            return
        earned = int(account.total_spend // rule.threshold)
        already_given = _reward_count_for_rule(db, account.id, rule.id)
        for _ in range(earned - already_given):
            db.add(
                Reward(
                    business_id=business_id, account_id=account.id, rule_id=rule.id,
                    reward_type=rule.reward_type, reward_value=rule.reward_value,
                )
            )

    elif rule.rule_type == RuleType.POINTS_PER_AMOUNT:
        if rule.threshold <= 0:
            return
        points_per_unit = rule.reward_value or 1.0
        units = math.floor(float(account.total_spend) / rule.threshold)
        transactions_count = (
            db.query(LoyaltyTransaction)
            .filter(LoyaltyTransaction.account_id == account.id, LoyaltyTransaction.description == f"rule:{rule.id}")
            .count()
        )
        new_units = units - transactions_count
        if new_units > 0:
            points = new_units * points_per_unit
            account.points_balance = float(account.points_balance) + points
            db.add(
                LoyaltyTransaction(
                    business_id=business_id, account_id=account.id, points_delta=points,
                    description=f"rule:{rule.id}",
                )
            )

    db.flush()


def redeem_reward(db: Session, business_id: uuid.UUID, reward_id: uuid.UUID, order_id: uuid.UUID | None, staff_id: uuid.UUID) -> Reward:
    reward = db.query(Reward).filter(Reward.id == reward_id, Reward.business_id == business_id).first()
    if reward is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reward not found")
    if reward.is_redeemed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reward already redeemed")

    reward.is_redeemed = True
    db.add(
        Redemption(
            business_id=business_id, reward_id=reward.id, order_id=order_id, redeemed_by_staff_id=staff_id
        )
    )
    db.flush()
    return reward
