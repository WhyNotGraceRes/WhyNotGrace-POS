"""invoice series, bill void/print tracking, and per-business toggles

Revision ID: 0006_invoice_integrity
Revises: 0005_gst_and_charge_bands
Create Date: 2026-08-16

Existing bills are deliberately left with invoice_number NULL. They were
settled under the old timestamp-and-random `bill_number` and back-filling a
consecutive series onto them would invent history — the numbers would not
match anything already printed or filed. The new series starts at 1 for the
current financial year, which is also the cleanest thing to hand an
accountant: one scheme up to a date, another after it.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_invoice_integrity"
down_revision: Union[str, None] = "0005_gst_and_charge_bands"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('''
CREATE TABLE invoice_counters (
	business_id UUID NOT NULL,
	series VARCHAR(10) NOT NULL,
	financial_year VARCHAR(8) NOT NULL,
	last_number INTEGER NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_invoice_counter_scope UNIQUE (business_id, series, financial_year),
	CONSTRAINT ck_invoice_counter_non_negative CHECK (last_number >= 0),
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE
);

CREATE INDEX ix_invoice_counters_business_id ON invoice_counters (business_id);

CREATE TABLE business_toggles (
	business_id UUID NOT NULL,
	key VARCHAR(100) NOT NULL,
	enabled BOOLEAN NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_business_toggle_key UNIQUE (business_id, key),
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE
);

CREATE INDEX ix_business_toggles_business_id ON business_toggles (business_id);

ALTER TABLE bills
	ADD COLUMN invoice_number VARCHAR(20),
	ADD COLUMN invoice_series VARCHAR(10),
	ADD COLUMN invoice_financial_year VARCHAR(8),
	ADD COLUMN invoice_sequence INTEGER,
	ADD COLUMN finalised_at TIMESTAMP WITH TIME ZONE,
	ADD COLUMN voided_at TIMESTAMP WITH TIME ZONE,
	ADD COLUMN void_reason VARCHAR(255),
	ADD COLUMN voided_by_user_id UUID REFERENCES users (id) ON DELETE SET NULL,
	ADD COLUMN print_count INTEGER NOT NULL DEFAULT 0,
	ADD COLUMN first_printed_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX ix_bills_invoice_number ON bills (invoice_number);

-- The series must be unique per business per financial year. A partial
-- index so the many NULLs (open bills, and every pre-existing bill) do not
-- collide with each other — in Postgres NULLs are distinct anyway, but
-- stating it makes the intent explicit and keeps the index small.
CREATE UNIQUE INDEX uq_bills_invoice_series_number
	ON bills (business_id, invoice_series, invoice_financial_year, invoice_sequence)
	WHERE invoice_sequence IS NOT NULL;
''')


def downgrade() -> None:
    op.execute('''
DROP INDEX IF EXISTS uq_bills_invoice_series_number;
DROP INDEX IF EXISTS ix_bills_invoice_number;

ALTER TABLE bills
	DROP COLUMN IF EXISTS invoice_number,
	DROP COLUMN IF EXISTS invoice_series,
	DROP COLUMN IF EXISTS invoice_financial_year,
	DROP COLUMN IF EXISTS invoice_sequence,
	DROP COLUMN IF EXISTS finalised_at,
	DROP COLUMN IF EXISTS voided_at,
	DROP COLUMN IF EXISTS void_reason,
	DROP COLUMN IF EXISTS voided_by_user_id,
	DROP COLUMN IF EXISTS print_count,
	DROP COLUMN IF EXISTS first_printed_at;

DROP TABLE IF EXISTS business_toggles;
DROP TABLE IF EXISTS invoice_counters;
''')
