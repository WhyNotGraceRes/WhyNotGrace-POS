import uuid

from pydantic import BaseModel, Field

from app.models.enums import ChargeBasis, PricingContext


class ChargeBandBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    applies_to_context: PricingContext | None = None
    # Half-open: min is included, max is not. See app/models/charge.py for
    # why — inclusive upper bounds leave paise-sized gaps between bands.
    min_amount: float = Field(ge=0)
    max_amount: float | None = Field(default=None, ge=0)
    basis: ChargeBasis = ChargeBasis.FLAT
    value: float = Field(ge=0)
    is_taxable: bool = True
    is_active: bool = True
    display_order: int = 0


class ChargeBandCreate(ChargeBandBase):
    pass


class ChargeBandUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    applies_to_context: PricingContext | None = None
    min_amount: float | None = Field(default=None, ge=0)
    max_amount: float | None = Field(default=None, ge=0)
    basis: ChargeBasis | None = None
    value: float | None = Field(default=None, ge=0)
    is_taxable: bool | None = None
    is_active: bool | None = None
    display_order: int | None = None


class ChargeBandOut(ChargeBandBase):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class ChargeLadderGap(BaseModel):
    """An uncovered stretch of a ladder. Surfaced so the admin screen can
    warn about a likely mistyped boundary — not treated as an error, since a
    charge that only applies in one range is legitimate."""

    name: str
    applies_to_context: PricingContext | None
    from_amount: float
    # None means "and above" — the ladder has no open-ended top band.
    to_amount: float | None


class ChargeBandListOut(BaseModel):
    bands: list[ChargeBandOut]
    gaps: list[ChargeLadderGap]


class ChargePreviewRequest(BaseModel):
    """Lets the owner check what a given order value would actually be
    charged, without having to create a real order to find out."""

    amount: float = Field(ge=0)
    context: PricingContext | None = None


class ChargePreviewLine(BaseModel):
    name: str
    basis: ChargeBasis
    value: float
    amount: float
    is_taxable: bool


class ChargePreviewOut(BaseModel):
    amount: float
    charges: list[ChargePreviewLine]
    charges_total: float
    taxable_value: float
    tax_lines: list[dict]
    tax_total: float
    grand_total: float
