import uuid

from pydantic import BaseModel, Field

from app.models.enums import BillStatus


class BillTaxCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    percent: float = Field(ge=0, le=100)


class BillDiscountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    percent: float | None = Field(default=None, ge=0, le=100)
    amount: float | None = Field(default=None, ge=0)
    reason: str | None = None


class BillServiceChargeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    percent: float = Field(ge=0, le=100)


class BillItemOut(BaseModel):
    id: uuid.UUID
    item_name_snapshot: str
    quantity: float
    unit_price: float
    line_total: float

    model_config = {"from_attributes": True}


class BillLineOut(BaseModel):
    id: uuid.UUID
    name: str
    percent: float | None = None
    amount: float

    model_config = {"from_attributes": True}


class BillOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    location_id: uuid.UUID | None
    bill_number: str
    status: BillStatus
    subtotal: float
    tax_total: float
    service_charge_total: float
    discount_total: float
    grand_total: float
    amount_paid: float
    items: list[BillItemOut] = Field(default_factory=list)
    taxes: list[BillLineOut] = Field(default_factory=list)
    discounts: list[BillLineOut] = Field(default_factory=list)
    service_charges: list[BillLineOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class GenerateBillRequest(BaseModel):
    session_id: uuid.UUID
    taxes: list[BillTaxCreate] = Field(default_factory=list)
    service_charges: list[BillServiceChargeCreate] = Field(default_factory=list)
    use_default_tax: bool = True
    use_default_service_charge: bool = True


class ApplyDiscountRequest(BillDiscountCreate):
    pass
