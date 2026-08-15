import uuid

from pydantic import BaseModel, Field

from app.models.enums import BusinessType


class BusinessOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    business_type: BusinessType
    is_active: bool

    model_config = {"from_attributes": True}


class BusinessUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    business_type: BusinessType | None = None
