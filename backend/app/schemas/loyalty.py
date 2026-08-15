import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LoyaltyRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    rule_type: str = Field(description="ORDER_COUNT_THRESHOLD | SPEND_THRESHOLD | POINTS_PER_AMOUNT | CUSTOM")
    threshold: float = Field(gt=0)
    reward_type: str = Field(description="FREE_ITEM | DISCOUNT_PERCENT | DISCOUNT_AMOUNT | POINTS")
    reward_value: float | None = None
    description: str | None = None


class LoyaltyRuleUpdate(BaseModel):
    name: str | None = None
    threshold: float | None = Field(default=None, gt=0)
    reward_value: float | None = None
    is_active: bool | None = None
    description: str | None = None


class LoyaltyRuleOut(BaseModel):
    id: uuid.UUID
    name: str
    rule_type: str
    threshold: float
    reward_type: str
    reward_value: float | None
    is_active: bool
    description: str | None

    model_config = {"from_attributes": True}


class LoyaltyAccountOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    total_orders: int
    total_spend: float
    points_balance: float

    model_config = {"from_attributes": True}


class RewardOut(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    rule_id: uuid.UUID
    reward_type: str
    reward_value: float | None
    is_redeemed: bool
    expires_at: datetime | None

    model_config = {"from_attributes": True}


class RedeemRewardRequest(BaseModel):
    order_id: uuid.UUID | None = None
