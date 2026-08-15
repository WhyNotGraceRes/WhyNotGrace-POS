import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole


class StaffCreateRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    mobile: str = Field(min_length=7, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole


class StaffUpdateRequest(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    role: UserRole | None = None
    is_active: bool | None = None


class StaffOut(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    mobile: str
    role: UserRole
    is_active: bool
    is_email_verified: bool

    model_config = {"from_attributes": True}
