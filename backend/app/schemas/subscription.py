import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

# A business with no Subscription row yet is NOT_CONFIGURED — a real,
# expected, honest state (most businesses start here), not an error.
# Kept as a plain Literal (not app.models.enums.SubscriptionStatus) since
# NOT_CONFIGURED never exists as a stored row — see subscription_service.py.
SubscriptionStatusOut = Literal["NOT_CONFIGURED", "PENDING", "ACTIVE", "PAYMENT_FAILED", "CANCELLED", "EXPIRED"]


class SubscriptionOut(BaseModel):
    status: SubscriptionStatusOut
    plan_name: str
    amount: float
    currency: str
    billing_interval: str
    subscription_id: uuid.UUID | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancelled_at: datetime | None = None


class SubscriptionCheckoutResponse(BaseModel):
    subscription_payment_id: uuid.UUID
    razorpay_order_id: str
    razorpay_key_id: str
    amount_paise: int
    currency: str = "INR"


class SubscriptionVerifyRequest(BaseModel):
    subscription_payment_id: uuid.UUID
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
