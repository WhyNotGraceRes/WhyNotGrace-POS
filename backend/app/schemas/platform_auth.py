import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import PlatformRole


class PlatformLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class PlatformUserOut(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    role: PlatformRole

    model_config = {"from_attributes": True}


class PlatformTokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: PlatformUserOut


class PlatformRefreshRequest(BaseModel):
    refresh_token: str


class PlatformAccessTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class PlatformLogoutRequest(BaseModel):
    refresh_token: str


class GenericMessageResponse(BaseModel):
    message: str
