import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Owner-facing: provisioning
# ---------------------------------------------------------------------------

class PartnerChannelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class PartnerChannelOut(BaseModel):
    id: uuid.UUID
    name: str
    key_id: str
    is_active: bool
    revoked_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PartnerChannelWithSecretOut(PartnerChannelOut):
    """Returned ONLY by create and rotate.

    The secret is not stored in a readable form and no other endpoint can
    produce it, so this response is the single opportunity to capture it.
    """

    secret: str


class PartnerMenuMapCreate(BaseModel):
    external_ref: str = Field(min_length=1, max_length=200)
    menu_item_id: uuid.UUID
    variant_id: uuid.UUID | None = None


class PartnerMenuMapOut(BaseModel):
    id: uuid.UUID
    external_ref: str
    menu_item_id: uuid.UUID
    variant_id: uuid.UUID | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Partner-facing: order submission
# ---------------------------------------------------------------------------

class PartnerOrderLine(BaseModel):
    """Note what is absent: there is no price field, and no way to add one.

    A partner names the item it wants by its own reference and says how
    many. Everything monetary is resolved server-side from that, so the
    request cannot express "this dish costs ₹1" even if the sending site is
    fully compromised.
    """

    external_ref: str = Field(min_length=1, max_length=200)
    quantity: int = Field(gt=0, le=50)
    special_instructions: str | None = Field(default=None, max_length=500)


class PartnerCustomerInfo(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    mobile: str = Field(min_length=7, max_length=20)


class PartnerOrderCreate(BaseModel):
    items: list[PartnerOrderLine] = Field(min_length=1, max_length=100)
    fulfilment: Literal["PICKUP", "DELIVERY"] = "PICKUP"
    customer: PartnerCustomerInfo | None = None
    notes: str | None = Field(default=None, max_length=1000)
    delivery_address: str | None = Field(default=None, max_length=500)
    delivery_instructions: str | None = Field(default=None, max_length=1000)
    # Supplied by the partner so a retry after a timeout resolves to the same
    # order instead of a second one. Optional, but strongly recommended —
    # without it a network blip becomes a duplicate ticket in the kitchen.
    idempotency_key: str | None = Field(default=None, max_length=255)


class PartnerOrderAck(BaseModel):
    """Deliberately thin.

    A partner needs to know its order was accepted and how to refer to it
    later. It does not need the full OrderOut, which carries pricing
    internals, session ids, and staff-facing fields that a channel
    credential has no business reading.
    """

    order_id: uuid.UUID
    order_number: str
    status: str
    subtotal: float
    duplicate: bool = False
