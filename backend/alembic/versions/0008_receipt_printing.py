"""printable receipt identity and kitchen stations

Revision ID: 0008_receipt_printing
Revises: 0007_refunds_and_round_off
Create Date: 2026-08-16

A printed tax invoice has to carry things the database had nowhere to put:
the FSSAI licence number every licensed food business in India must show, and
the address/footer lines an owner wants under their name. Kitchen stations
land here too, so one order can print a tandoor ticket and a Chinese ticket
instead of one sheet the whole kitchen has to read past.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_receipt_printing"
down_revision: Union[str, None] = "0007_refunds_and_round_off"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('''
ALTER TABLE business_settings
	ADD COLUMN fssai_number VARCHAR(30),
	ADD COLUMN receipt_header_lines TEXT,
	ADD COLUMN receipt_footer_text TEXT;

-- NULL means the default kitchen, so every existing business keeps printing
-- exactly one ticket per order until someone configures stations.
ALTER TABLE menu_items
	ADD COLUMN kitchen_station VARCHAR(50);
''')


def downgrade() -> None:
    op.execute('''
ALTER TABLE menu_items DROP COLUMN IF EXISTS kitchen_station;

ALTER TABLE business_settings
	DROP COLUMN IF EXISTS fssai_number,
	DROP COLUMN IF EXISTS receipt_header_lines,
	DROP COLUMN IF EXISTS receipt_footer_text;
''')
