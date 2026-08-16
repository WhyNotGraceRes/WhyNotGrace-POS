import uuid

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, description="Email address or mobile number")
    password: str = Field(min_length=1)


class UserOut(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    mobile: str
    role: UserRole
    is_email_verified: bool

    model_config = {"from_attributes": True}


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LogoutRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self) -> "ResetPasswordRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("new_password and confirm_password do not match")
        return self


class GenericMessageResponse(BaseModel):
    message: str
