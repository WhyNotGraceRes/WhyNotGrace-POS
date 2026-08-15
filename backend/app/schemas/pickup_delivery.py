import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import DeliveryStatus
from app.schemas.order import OrderItemCreate, OrderOut


class PublicCustomerInfo(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    mobile: str = Field(min_length=7, max_length=20)
    email: EmailStr | None = None


class PickupCheckoutRequest(BaseModel):
    customer: PublicCustomerInfo
    items: list[OrderItemCreate] = Field(min_length=1)
    notes: str | None = None


class DeliveryCheckoutRequest(BaseModel):
    customer: PublicCustomerInfo
    items: list[OrderItemCreate] = Field(min_length=1)
    delivery_address: str = Field(min_length=5, max_length=1000)
    delivery_instructions: str | None = Field(default=None, max_length=1000)
    notes: str | None = None


class CheckoutResponse(BaseModel):
    order: OrderOut
    payment_id: uuid.UUID
    razorpay_order_id: str
    razorpay_key_id: str
    amount_paise: int
    currency: str = "INR"


class CheckoutVerifyRequest(BaseModel):
    payment_id: uuid.UUID
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class DeliveryStatusUpdateRequest(BaseModel):
    status: DeliveryStatus
