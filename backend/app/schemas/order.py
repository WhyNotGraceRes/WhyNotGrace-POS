import uuid

from pydantic import BaseModel, Field

from app.models.enums import OrderSource, OrderStatus, PricingContext


class OrderItemCreate(BaseModel):
    menu_item_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    quantity: int = Field(gt=0, le=50)
    option_ids: list[uuid.UUID] = Field(default_factory=list)
    special_instructions: str | None = Field(default=None, max_length=500)


class OrderCreateRequest(BaseModel):
    location_id: uuid.UUID | None = None
    source: OrderSource
    pricing_context: PricingContext
    items: list[OrderItemCreate] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=1000)
    delivery_address: str | None = None
    delivery_instructions: str | None = Field(default=None, max_length=1000)
    customer_id: uuid.UUID | None = None


class OrderItemOptionOut(BaseModel):
    option_id: uuid.UUID
    option_name_snapshot: str
    price_delta_snapshot: float

    model_config = {"from_attributes": True}


class OrderItemOut(BaseModel):
    id: uuid.UUID
    menu_item_id: uuid.UUID
    variant_id: uuid.UUID | None
    item_name_snapshot: str
    quantity: int
    unit_price: float
    line_total: float
    special_instructions: str | None
    options: list[OrderItemOptionOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class OrderCustomerBriefOut(BaseModel):
    id: uuid.UUID
    first_name: str
    mobile: str

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    location_id: uuid.UUID | None
    customer_id: uuid.UUID | None
    customer: OrderCustomerBriefOut | None = None
    order_number: str
    source: OrderSource
    pricing_context: PricingContext
    status: OrderStatus
    is_additional: bool
    subtotal: float
    notes: str | None
    delivery_address: str | None = None
    delivery_status: str | None = None
    delivery_instructions: str | None = None
    items: list[OrderItemOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class OrderStatusUpdateRequest(BaseModel):
    status: OrderStatus
