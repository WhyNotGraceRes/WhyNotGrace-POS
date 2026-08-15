import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import KOTStatus


class KOTItemOut(BaseModel):
    id: uuid.UUID
    item_name_snapshot: str
    quantity: int
    options_summary: str | None

    model_config = {"from_attributes": True}


class KOTOut(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    location_id: uuid.UUID | None
    kot_number: str
    status: KOTStatus
    special_instructions: str | None
    estimated_minutes: int | None
    created_at: datetime
    items: list[KOTItemOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class KOTStatusUpdateRequest(BaseModel):
    status: KOTStatus
    estimated_minutes: int | None = None
