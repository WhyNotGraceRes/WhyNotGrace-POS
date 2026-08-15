import uuid

from pydantic import BaseModel, Field


class MenuCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    display_order: int = 0


class MenuCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    display_order: int | None = None
    is_active: bool | None = None


class MenuCategoryOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    display_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class MenuOptionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price_delta: float = 0
    display_order: int = 0


class MenuOptionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    price_delta: float | None = None
    display_order: int | None = None
    is_active: bool | None = None


class MenuOptionOut(BaseModel):
    id: uuid.UUID
    name: str
    price_delta: float
    is_active: bool
    display_order: int

    model_config = {"from_attributes": True}


class MenuOptionGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    is_required: bool = False
    allow_multiple: bool = False
    display_order: int = 0
    options: list[MenuOptionCreate] = Field(default_factory=list)


class MenuOptionGroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_required: bool | None = None
    allow_multiple: bool | None = None
    display_order: int | None = None
    is_active: bool | None = None


class MenuOptionGroupOut(BaseModel):
    id: uuid.UUID
    name: str
    is_required: bool
    allow_multiple: bool
    display_order: int
    is_active: bool
    options: list[MenuOptionOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class MenuVariantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price_delta: float = 0
    is_default: bool = False


class MenuVariantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    price_delta: float | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class MenuVariantOut(BaseModel):
    id: uuid.UUID
    name: str
    price_delta: float
    is_default: bool
    is_active: bool

    model_config = {"from_attributes": True}


class MenuItemCreate(BaseModel):
    category_id: uuid.UUID
    kitchen_station: str | None = Field(default=None, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    base_price: float = Field(gt=0)
    is_veg: bool = True
    image_url: str | None = None
    display_order: int = 0
    variants: list[MenuVariantCreate] = Field(default_factory=list)
    option_groups: list[MenuOptionGroupCreate] = Field(default_factory=list)


class MenuItemUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    kitchen_station: str | None = Field(default=None, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    base_price: float | None = Field(default=None, gt=0)
    is_veg: bool | None = None
    image_url: str | None = None
    display_order: int | None = None
    is_active: bool | None = None
    is_sold_out: bool | None = None
    is_todays_special: bool | None = None
    is_specialty: bool | None = None


class MenuItemOut(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    kitchen_station: str | None = None
    name: str
    description: str | None
    base_price: float
    is_veg: bool
    is_active: bool
    is_sold_out: bool
    is_todays_special: bool
    is_specialty: bool
    image_url: str | None
    display_order: int
    variants: list[MenuVariantOut] = Field(default_factory=list)
    option_groups: list[MenuOptionGroupOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}
