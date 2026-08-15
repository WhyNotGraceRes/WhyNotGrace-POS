import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.enums import BusinessType, UserRole


class RegisterRequest(BaseModel):
    business_name: str = Field(min_length=2, max_length=200)
    business_type: BusinessType
    owner_first_name: str = Field(min_length=1, max_length=100)
    owner_last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    mobile: str = Field(min_length=7, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        digits = v.replace("+", "").replace(" ", "").replace("-", "")
        if not digits.isdigit():
            raise ValueError("Mobile number must contain only digits, spaces, +, or -")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("password and confirm_password do not match")
        return self


class RegisterResponse(BaseModel):
    business_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    message: str = "Registration successful. Please check your email for a verification code."


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ResendVerificationRequest(BaseModel):
    email: EmailStr


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
