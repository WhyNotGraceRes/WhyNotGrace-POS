"""Optional stock_quantity on menu items. NULL (the default, and every
existing row after this migration) means untracked/unlimited, matching
current behavior exactly — a business only opts into stock tracking by
setting a number. See pricing_service.compute_line_item for the
decrement-and-auto-sold-out behavior once it's set.

Revision ID: 0015_menu_item_stock
Revises: 0014_notifications
Create Date: 2026-08-17
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0015_menu_item_stock"
down_revision: Union[str, None] = "0014_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('''
ALTER TABLE menu_items ADD COLUMN stock_quantity INTEGER;
''')


def downgrade() -> None:
    op.execute('''
ALTER TABLE menu_items DROP COLUMN IF EXISTS stock_quantity;
''')
