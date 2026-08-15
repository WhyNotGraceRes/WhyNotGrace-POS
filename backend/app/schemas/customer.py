import uuid
from datetime import date

from pydantic import BaseModel, EmailStr, Field


class CustomerCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    mobile: str = Field(min_length=7, max_length=20)
    birthday: date | None = None
    email: EmailStr | None = None
    marketing_opt_in: bool = False
    sms_opt_in: bool = False
    email_opt_in: bool = False
    whatsapp_opt_in: bool = False


class CustomerUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    birthday: date | None = None
    email: EmailStr | None = None
    marketing_opt_in: bool | None = None
    sms_opt_in: bool | None = None
    email_opt_in: bool | None = None
    whatsapp_opt_in: bool | None = None


class CustomerOut(BaseModel):
    id: uuid.UUID
    first_name: str
    mobile: str
    birthday: date | None
    email: str | None
    marketing_opt_in: bool
    sms_opt_in: bool
    email_opt_in: bool
    whatsapp_opt_in: bool

    model_config = {"from_attributes": True}
