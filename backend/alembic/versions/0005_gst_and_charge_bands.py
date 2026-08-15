"""GST invoice fields and owner-defined value-based charge bands

Revision ID: 0005_gst_and_charge_bands
Revises: 0004_partner_channels
Create Date: 2026-08-15

Schema half of the GST correctness work. The arithmetic fix itself lives in
billing_service._recompute_totals and needs no migration — but it does change
what future bills total to, so note that already-PAID bills are left exactly
as they are: their stored totals are what the guest actually paid and what
was reported, and silently restating history would be worse than the bug.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_gst_and_charge_bands"
down_revision: Union[str, None] = "0004_partner_channels"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('''
CREATE TYPE chargebasis AS ENUM ('PERCENT', 'FLAT');

ALTER TABLE business_settings
    ADD COLUMN gstin VARCHAR(20),
    ADD COLUMN tax_label VARCHAR(40) NOT NULL DEFAULT 'GST',
    ADD COLUMN tax_split_intra_state BOOLEAN NOT NULL DEFAULT TRUE;

-- percent becomes nullable so a FLAT band can record "no percentage"
-- rather than a fabricated one that would misrepresent the bill.
ALTER TABLE bill_service_charges
    ALTER COLUMN percent DROP NOT NULL,
    ADD COLUMN is_taxable BOOLEAN NOT NULL DEFAULT TRUE;

CREATE TABLE charge_bands (
	business_id UUID NOT NULL,
	name VARCHAR(100) NOT NULL,
	applies_to_context pricingcontext,
	min_amount NUMERIC(10, 2) NOT NULL,
	max_amount NUMERIC(10, 2),
	basis chargebasis NOT NULL,
	value NUMERIC(10, 2) NOT NULL,
	is_taxable BOOLEAN NOT NULL,
	is_active BOOLEAN NOT NULL,
	display_order INTEGER NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_charge_band_ladder_start UNIQUE (business_id, name, applies_to_context, min_amount),
	CONSTRAINT ck_charge_band_range CHECK (max_amount IS NULL OR max_amount > min_amount),
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE
);

CREATE INDEX ix_charge_bands_business_id ON charge_bands (business_id);
''')


def downgrade() -> None:
    op.execute('''
DROP TABLE IF EXISTS charge_bands;
DROP TYPE IF EXISTS chargebasis;

ALTER TABLE bill_service_charges
    DROP COLUMN IF EXISTS is_taxable;

-- Restoring NOT NULL would fail against any row written by a FLAT band, so
-- fill those in first. 0 is the honest value: the charge genuinely had no
-- percentage behind it.
UPDATE bill_service_charges SET percent = 0 WHERE percent IS NULL;
ALTER TABLE bill_service_charges ALTER COLUMN percent SET NOT NULL;

ALTER TABLE business_settings
    DROP COLUMN IF EXISTS gstin,
    DROP COLUMN IF EXISTS tax_label,
    DROP COLUMN IF EXISTS tax_split_intra_state;
''')
