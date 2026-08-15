import uuid

from pydantic import BaseModel


class WebsiteConfigOut(BaseModel):
    is_published: bool
    logo_url: str | None
    hero_image_url: str | None
    story: str | None
    contact_phone: str | None
    contact_email: str | None
    contact_address: str | None
    theme_color: str | None

    model_config = {"from_attributes": True}


class WebsiteConfigUpdateRequest(BaseModel):
    is_published: bool | None = None
    logo_url: str | None = None
    hero_image_url: str | None = None
    story: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    contact_address: str | None = None
    theme_color: str | None = None


class PublicWebsiteResponse(BaseModel):
    business_id: uuid.UUID
    business_name: str
    business_type: str
    config: WebsiteConfigOut
    pickup_enabled: bool
    delivery_enabled: bool
