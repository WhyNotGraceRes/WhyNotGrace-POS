from pydantic import BaseModel, Field

from app.core.toggles import ToggleGroup


class ToggleOut(BaseModel):
    key: str
    group: ToggleGroup
    enabled: bool
    # True when this business explicitly chose a value, false when it is
    # following the registry default. The screen shows these differently so a
    # later change of default is not mistaken for someone's setting.
    is_overridden: bool
    default: bool
    # False means an entitlement: shown, explained, but not editable here.
    owner_editable: bool
    label: str
    description: str
    warning: str | None = None


class ToggleUpdateRequest(BaseModel):
    enabled: bool


class InvoiceSeriesOut(BaseModel):
    """Shown on the settings screen so an owner can see their series without
    having to settle a bill to find out what it looks like."""

    series: str
    financial_year: str
    next_number: str
    last_issued: int = Field(ge=0)
