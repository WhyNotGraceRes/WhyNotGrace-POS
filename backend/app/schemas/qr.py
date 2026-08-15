import uuid

from pydantic import BaseModel, Field

from app.models.enums import LocationType


class QRScanResponse(BaseModel):
    session_token: str
    business_id: uuid.UUID
    business_name: str
    location_id: uuid.UUID
    location_type: LocationType
    location_name: str
    expires_at: str


class QRMenuOptionOut(BaseModel):
    id: uuid.UUID
    name: str
    price_delta: float


class QRMenuOptionGroupOut(BaseModel):
    id: uuid.UUID
    name: str
    is_required: bool
    allow_multiple: bool
    options: list[QRMenuOptionOut]


class QRMenuVariantOut(BaseModel):
    id: uuid.UUID
    name: str
    price_delta: float
    is_default: bool


class QRMenuItemOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    price: float
    is_veg: bool
    is_sold_out: bool
    is_todays_special: bool
    is_specialty: bool
    image_url: str | None
    variants: list[QRMenuVariantOut]
    option_groups: list[QRMenuOptionGroupOut]


class QRMenuCategoryOut(BaseModel):
    id: uuid.UUID
    name: str
    items: list[QRMenuItemOut]


class QRMenuResponse(BaseModel):
    business_name: str
    location_name: str
    pricing_context: str
    categories: list[QRMenuCategoryOut]


class QRCartItem(BaseModel):
    menu_item_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    quantity: int = Field(gt=0, le=50)
    option_ids: list[uuid.UUID] = Field(default_factory=list)
    special_instructions: str | None = None


class QROrderCreateRequest(BaseModel):
    items: list[QRCartItem] = Field(min_length=1)
    notes: str | None = None
