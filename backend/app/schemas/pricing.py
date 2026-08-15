import uuid

from pydantic import BaseModel, Field

from app.models.enums import PricingContext


class PriceRuleCreate(BaseModel):
    item_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    context: PricingContext
    price: float = Field(gt=0)


class PriceRuleUpdate(BaseModel):
    price: float | None = Field(default=None, gt=0)
    is_active: bool | None = None


class PriceRuleOut(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID
    variant_id: uuid.UUID | None
    context: PricingContext
    price: float
    is_active: bool

    model_config = {"from_attributes": True}
