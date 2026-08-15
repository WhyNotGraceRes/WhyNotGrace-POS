"""Allocating tax invoice numbers.

The rule being satisfied: a consecutive serial, unique within the financial
year, at most 16 characters (CGST Rule 46). Two design points carry most of
the weight:

**Allocated at settlement, not at bill creation.** A bill is opened long
before it is paid, and plenty of opened bills never get paid — the table
merges, the order is cancelled, the guest walks out. If the number were
stamped at creation, every one of those would burn a serial and leave a hole
in a series that is required to have none.

**A locked counter row, not a Postgres sequence.** A sequence is explicitly
not gapless: it hands out a value and keeps it even when the transaction
rolls back. That is the precise failure this exists to prevent. The row lock
costs nothing at restaurant volume — 2,000 bills a day is one update every
forty seconds — and gives a genuinely consecutive series.
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core import toggles
from app.models.invoice import InvoiceCounter

DEFAULT_SERIES = "INV"

# Indian financial year starts on 1 April.
_FY_START_MONTH = 4


def financial_year_code(on: date | None = None) -> str:
    """"2627" for FY 2026-27.

    Four digits rather than the full years so the whole invoice number fits
    inside the 16-character limit with room for a meaningful sequence.
    """
    today = on or datetime.now(timezone.utc).date()
    start_year = today.year if today.month >= _FY_START_MONTH else today.year - 1
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def format_invoice_number(series: str, financial_year: str, sequence: int) -> str:
    """e.g. INV/2627/000001 — 15 characters at six digits, one inside the
    16-character limit.

    Six digits covers a million invoices per financial year, which no single
    restaurant approaches. The format does not hard-break at exactly a
    million (INV/2627/1000000 is still 16 characters and legal); it breaks at
    ten million. `allocate` checks the produced length rather than assuming
    any of this, so the limit is enforced by measurement, not by arithmetic
    done in a docstring.
    """
    if financial_year:
        return f"{series}/{financial_year}/{sequence:06d}"
    return f"{series}/{sequence:06d}"


def allocate(
    db: Session,
    business_id: uuid.UUID,
    *,
    series: str = DEFAULT_SERIES,
    on: date | None = None,
) -> tuple[str, str, str, int]:
    """Reserves the next number. Returns (number, series, financial_year, sequence).

    Must be called inside the same transaction as whatever is being
    numbered: if that transaction rolls back, the counter increment rolls
    back with it and the number is genuinely reusable rather than lost.
    """
    per_year = toggles.is_enabled(db, business_id, toggles.INVOICE_SERIES_PER_YEAR)
    fy = financial_year_code(on) if per_year else ""

    # Create-if-missing must be atomic, not check-then-insert. The very first
    # settlement for a business can arrive on several connections at once, and
    # a SELECT-then-INSERT has every one of them find nothing and then race to
    # insert — all but one dying on the unique constraint. ON CONFLICT DO
    # NOTHING makes the create a no-op for the losers instead of an error.
    now = datetime.now(timezone.utc)
    db.execute(
        pg_insert(InvoiceCounter)
        .values(
            id=uuid.uuid4(), business_id=business_id, series=series,
            financial_year=fy, last_number=0, created_at=now, updated_at=now,
        )
        .on_conflict_do_nothing(constraint="uq_invoice_counter_scope")
    )

    # Now the row certainly exists. with_for_update serialises concurrent
    # settlements on it: without the lock, two cashiers pressing Settle at the
    # same instant both read the same last_number and both write the same next
    # one. If another transaction created the row and has not committed yet,
    # this blocks until it does — which is exactly the intended queueing.
    counter = db.execute(
        select(InvoiceCounter)
        .where(
            InvoiceCounter.business_id == business_id,
            InvoiceCounter.series == series,
            InvoiceCounter.financial_year == fy,
        )
        .with_for_update()
    ).scalar_one()

    counter.last_number += 1
    sequence = counter.last_number
    db.flush()

    number = format_invoice_number(series, fy, sequence)
    if len(number) > 16:
        # Rule 46 caps the number at 16 characters. Reaching this means a
        # business has issued a million invoices in one financial year, which
        # deserves a real decision about the series rather than silently
        # emitting a non-compliant number.
        raise ValueError(
            f"Invoice number {number!r} exceeds the 16-character limit. "
            "Start a new series for this business."
        )
    return number, series, fy, sequence


def peek_next(db: Session, business_id: uuid.UUID, *, series: str = DEFAULT_SERIES) -> str:
    """What the next number would be, without consuming it. For showing the
    owner their series on the settings screen."""
    per_year = toggles.is_enabled(db, business_id, toggles.INVOICE_SERIES_PER_YEAR)
    fy = financial_year_code() if per_year else ""
    counter = (
        db.query(InvoiceCounter)
        .filter(
            InvoiceCounter.business_id == business_id,
            InvoiceCounter.series == series,
            InvoiceCounter.financial_year == fy,
        )
        .first()
    )
    return format_invoice_number(series, fy, (counter.last_number if counter else 0) + 1)
