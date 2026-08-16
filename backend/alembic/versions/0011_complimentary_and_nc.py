"""complimentary lines, and no-charge bills

Revision ID: 0011_complimentary_and_nc
Revises: 0010_void_bill_item
Create Date: 2026-08-16
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011_complimentary_and_nc"
down_revision: Union[str, None] = "0010_void_bill_item"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # All nullable with no default: an existing line is not comped and an
    # existing bill is not no-charge, which is what NULL already says.
    op.execute('''
ALTER TABLE bill_items
	ADD COLUMN comped_at TIMESTAMP WITH TIME ZONE,
	ADD COLUMN comp_reason VARCHAR(255),
	ADD COLUMN comped_by_user_id UUID REFERENCES users (id) ON DELETE SET NULL;

ALTER TABLE bills
	ADD COLUMN nc_at TIMESTAMP WITH TIME ZONE,
	ADD COLUMN nc_reason VARCHAR(255),
	ADD COLUMN nc_by_user_id UUID REFERENCES users (id) ON DELETE SET NULL;

CREATE INDEX ix_bill_items_comped_at ON bill_items (comped_at) WHERE comped_at IS NOT NULL;
CREATE INDEX ix_bills_nc_at ON bills (nc_at) WHERE nc_at IS NOT NULL;
''')


def downgrade() -> None:
    op.execute('''
DROP INDEX IF EXISTS ix_bills_nc_at;
DROP INDEX IF EXISTS ix_bill_items_comped_at;

ALTER TABLE bills
	DROP COLUMN IF EXISTS nc_at,
	DROP COLUMN IF EXISTS nc_reason,
	DROP COLUMN IF EXISTS nc_by_user_id;

ALTER TABLE bill_items
	DROP COLUMN IF EXISTS comped_at,
	DROP COLUMN IF EXISTS comp_reason,
	DROP COLUMN IF EXISTS comped_by_user_id;
''')
