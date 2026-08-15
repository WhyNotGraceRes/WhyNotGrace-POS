"""Gapless invoice numbering.

A tax invoice number has to be a consecutive serial, unique within the
financial year, at most 16 characters (CGST Rule 46). The existing
`utils.numbering.generate_number` produces a timestamp plus random bytes and
says in its own docstring that it is "a display convenience only" — fine for
an order or KOT reference, not for an invoice.

One row per (business, series, financial year), holding the last number
issued. Allocation takes a row lock, so two cashiers settling at the same
instant queue rather than collide. At restaurant volume the lock is free:
even 2,000 bills a day is one row update every forty seconds.

Why a locked counter row rather than a Postgres SEQUENCE: a sequence is not
gapless. It hands out a number and keeps it even if the transaction rolls
back, which is exactly the hole in the series we are trying to avoid.
"""
import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class InvoiceCounter(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "invoice_counters"
    __table_args__ = (
        UniqueConstraint("business_id", "series", "financial_year", name="uq_invoice_counter_scope"),
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Lets one business run more than one series later (per outlet, or a
    # separate series for takeaway) without reworking the schema. One series
    # named "INV" today.
    series: Mapped[str] = mapped_column(String(10), nullable=False, default="INV")
    # "2627" for FY 2026-27. Empty string when the business has turned off
    # per-year restarting, so one continuous series shares a single row.
    financial_year: Mapped[str] = mapped_column(String(8), nullable=False)
    last_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
