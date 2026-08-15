import uuid

from pydantic import BaseModel, Field

from app.models.enums import LocationStatus, LocationType


class LocationCreate(BaseModel):
    location_type: LocationType
    name: str = Field(min_length=1, max_length=100)
    capacity: int | None = None
    floor: str | None = None
    room_type: str | None = None


class LocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    capacity: int | None = None
    floor: str | None = None
    room_type: str | None = None
    status: LocationStatus | None = None
    is_active: bool | None = None


class LocationOut(BaseModel):
    id: uuid.UUID
    location_type: LocationType
    name: str
    capacity: int | None
    floor: str | None
    room_type: str | None
    status: LocationStatus
    is_active: bool
    qr_url: str | None = None

    model_config = {"from_attributes": True}
