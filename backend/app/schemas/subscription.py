import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

# A business with no Subscription row yet is NOT_CONFIGURED — a real,
# expected, honest state (most businesses start here, before platform staff
# provision a plan), not an error. Kept as a plain Literal (not
# app.models.enums.SubscriptionStatus) since NOT_CONFIGURED never exists as
# a stored row — see subscription_service.py.
SubscriptionStatusOut = Literal[
    "NOT_CONFIGURED", "PENDING", "ACTIVE", "GRACE", "SUSPENDED", "PAYMENT_FAILED", "CANCELLED", "EXPIRED"
]


class SubscriptionOut(BaseModel):
    """plan_name/amount/etc. are optional now — a NOT_CONFIGURED business
    has no plan at all to show, and there is no longer one universal
    default plan the way the old ₹699/month self-serve one was.
    """
    status: SubscriptionStatusOut
    plan_name: str | None = None
    amount: float | None = None
    currency: str | None = None
    billing_interval: str | None = None
    subscription_id: uuid.UUID | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancelled_at: datetime | None = None
