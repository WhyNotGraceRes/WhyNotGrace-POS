import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import BusinessType, SubscriptionStatus


class ProvisionBusinessRequest(BaseModel):
    business_name: str = Field(min_length=2, max_length=200)
    business_type: BusinessType
    owner_first_name: str = Field(min_length=1, max_length=100)
    owner_last_name: str = Field(min_length=1, max_length=100)
    owner_email: EmailStr
    owner_mobile: str = Field(min_length=7, max_length=20)
    owner_password: str = Field(min_length=8, max_length=128)

    @field_validator("owner_mobile")
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        digits = v.replace("+", "").replace(" ", "").replace("-", "")
        if not digits.isdigit():
            raise ValueError("Mobile number must contain only digits, spaces, +, or -")
        return v


class ProvisionBusinessResponse(BaseModel):
    business_id: uuid.UUID
    owner_user_id: uuid.UUID
    owner_email: str


class PlatformBusinessOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    business_type: BusinessType
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SetBusinessActiveRequest(BaseModel):
    is_active: bool


class PlatformFeatureFlagUpdateRequest(BaseModel):
    enabled: bool


class PlatformToggleUpdateRequest(BaseModel):
    enabled: bool


class ProvisionSubscriptionRequest(BaseModel):
    plan_name: str = Field(min_length=1, max_length=50)
    amount: float = Field(ge=0)
    billing_interval: str = Field(default="monthly", max_length=20)
    months: int = Field(default=1, ge=1, le=60)


class RenewSubscriptionRequest(BaseModel):
    months: int = Field(default=1, ge=1, le=60)


class PlatformSubscriptionOut(BaseModel):
    status: SubscriptionStatus | str
    plan_name: str | None = None
    amount: float | None = None
    currency: str | None = None
    billing_interval: str | None = None
    subscription_id: uuid.UUID | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancelled_at: datetime | None = None
