import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import PaymentMethod, PaymentStatus


class CashPaymentRequest(BaseModel):
    bill_id: uuid.UUID
    amount: float = Field(gt=0)
    method: PaymentMethod = PaymentMethod.CASH
    notes: str | None = None


class RazorpayOrderCreateRequest(BaseModel):
    bill_id: uuid.UUID


class RazorpayOrderCreateResponse(BaseModel):
    payment_id: uuid.UUID
    razorpay_order_id: str
    razorpay_key_id: str
    amount_paise: int
    currency: str = "INR"


class RazorpayVerifyRequest(BaseModel):
    payment_id: uuid.UUID
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class PaymentOut(BaseModel):
    id: uuid.UUID
    bill_id: uuid.UUID
    method: PaymentMethod
    status: PaymentStatus
    amount: float
    provider: str | None
    provider_order_id: str | None
    provider_payment_id: str | None
    verified_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RefundRequest(BaseModel):
    payment_id: uuid.UUID
    amount: float = Field(gt=0)
    # Defaults to however the payment came in. Made explicit because money
    # often goes back a different way than it arrived — an online payment
    # refunded as cash at the counter is routine.
    method: PaymentMethod | None = None
    reason: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class RefundOut(BaseModel):
    id: uuid.UUID
    bill_id: uuid.UUID
    payment_id: uuid.UUID
    amount: float
    method: PaymentMethod
    reason: str | None
    refunded_at: datetime

    model_config = {"from_attributes": True}
