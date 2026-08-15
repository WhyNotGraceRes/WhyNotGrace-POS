import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.shift import ShiftStatus


class OpenShiftRequest(BaseModel):
    # Zero is legitimate — plenty of counters start with an empty drawer.
    opening_float: float = Field(default=0, ge=0)


class CloseShiftRequest(BaseModel):
    declared_cash: float = Field(ge=0)
    notes: str | None = Field(default=None, max_length=500)


class ShiftOut(BaseModel):
    id: uuid.UUID
    status: ShiftStatus
    opened_at: datetime
    closed_at: datetime | None
    opening_float: float
    declared_cash: float | None
    expected_cash: float | None
    variance: float | None
    notes: str | None

    model_config = {"from_attributes": True}


class ShiftPaymentLine(BaseModel):
    method: str
    count: int
    amount: float


class ShiftReportOut(BaseModel):
    """The Z-report.

    `expected_cash` is deliberately optional: while a shift is open and blind
    counting is on it comes back null, so the screen has nothing to show a
    cashier who has not counted yet.
    """

    shift_id: uuid.UUID
    status: str
    opened_at: datetime
    closed_at: datetime | None
    opened_by: str | None

    opening_float: float
    payments: list[ShiftPaymentLine]
    gross_takings: float
    cash_taken: float
    cash_returned: float

    refunds_count: int
    refunds_total: float
    bills_settled: int
    bills_voided: int
    discounts_total: float

    expected_cash: float | None
    declared_cash: float | None
    variance: float | None
    blind_count: bool
    notes: str | None
