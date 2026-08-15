import uuid
from datetime import datetime

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


class VoidBillRequest(BaseModel):
    """Reason is optional here and required by the service when the
    billing.void_requires_reason toggle is on, so the rule lives in one place
    rather than being duplicated as schema validation that a toggle cannot
    reach."""

    reason: str | None = Field(default=None, max_length=255)


class BillOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    location_id: uuid.UUID | None
    bill_number: str
    invoice_number: str | None = None
    finalised_at: datetime | None = None
    voided_at: datetime | None = None
    void_reason: str | None = None
    print_count: int = 0
    status: BillStatus
    subtotal: float
    tax_total: float
    service_charge_total: float
    discount_total: float
    round_off: float = 0
    grand_total: float
    amount_refunded: float = 0
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


class BillPrintOut(BaseModel):
    """The bill plus whether this particular copy must be stamped DUPLICATE.

    The flag is computed server-side rather than left to the client to work
    out from print_count, so a client that forgets the rule cannot print an
    unmarked second original.
    """

    bill: BillOut
    is_duplicate: bool
    print_count: int
