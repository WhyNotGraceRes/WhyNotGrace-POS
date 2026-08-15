from pydantic import BaseModel, Field


class BusinessSettingsOut(BaseModel):
    default_language: str
    supported_languages: str
    timezone: str
    default_tax_percent: float
    default_service_charge_percent: float
    currency: str

    model_config = {"from_attributes": True}


class BusinessSettingsUpdateRequest(BaseModel):
    default_language: str | None = Field(default=None, max_length=10)
    supported_languages: str | None = Field(default=None, max_length=100)
    timezone: str | None = Field(default=None, max_length=64)
    default_tax_percent: float | None = Field(default=None, ge=0, le=100)
    default_service_charge_percent: float | None = Field(default=None, ge=0, le=100)
    currency: str | None = Field(default=None, max_length=8)
