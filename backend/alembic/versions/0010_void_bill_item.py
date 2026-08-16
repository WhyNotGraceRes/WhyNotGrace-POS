"""voiding a single line on a bill

Revision ID: 0010_void_bill_item
Revises: 0009_shift_sessions
Create Date: 2026-08-16
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010_void_bill_item"
down_revision: Union[str, None] = "0009_shift_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable with no default: every existing line is un-voided, which is
    # what NULL already means here, so no backfill is needed.
    op.execute('''
ALTER TABLE bill_items
	ADD COLUMN voided_at TIMESTAMP WITH TIME ZONE,
	ADD COLUMN void_reason VARCHAR(255),
	ADD COLUMN voided_by_user_id UUID REFERENCES users (id) ON DELETE SET NULL;

CREATE INDEX ix_bill_items_voided_at ON bill_items (voided_at) WHERE voided_at IS NOT NULL;
''')


def downgrade() -> None:
    op.execute('''
DROP INDEX IF EXISTS ix_bill_items_voided_at;

ALTER TABLE bill_items
	DROP COLUMN IF EXISTS voided_at,
	DROP COLUMN IF EXISTS void_reason,
	DROP COLUMN IF EXISTS voided_by_user_id;
''')
