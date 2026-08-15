"""menu option group is_active + delivery status/instructions foundation

Revision ID: 0002_menu_crud_and_delivery
Revises: 0001_initial_schema
Create Date: 2026-08-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_menu_crud_and_delivery"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('''
ALTER TABLE menu_option_groups ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE orders ADD COLUMN delivery_instructions TEXT;
''')


def downgrade() -> None:
    op.execute('''
ALTER TABLE orders DROP COLUMN IF EXISTS delivery_instructions;
ALTER TABLE menu_option_groups DROP COLUMN IF EXISTS is_active;
''')
