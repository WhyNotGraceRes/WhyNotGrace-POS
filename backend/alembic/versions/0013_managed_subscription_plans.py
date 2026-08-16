"""GRACE and SUSPENDED subscription statuses, for the platform-managed plan
lifecycle (see app.services.subscription_service) that replaces self-serve
Razorpay checkout: 3 days past current_period_end with no renewal shows a
warning (GRACE), 3 days after that blocks dashboard login (SUSPENDED) until
platform staff renews or reactivates.

Revision ID: 0013_managed_subscription_plans
Revises: 0012_platform_users
Create Date: 2026-08-17
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0013_managed_subscription_plans"
down_revision: Union[str, None] = "0012_platform_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Same caveat as 0004_partner_channels: the test suite builds its schema
    # via Base.metadata.create_all() from the Python enum directly, so it
    # cannot catch a missing ADD VALUE here — any future SubscriptionStatus
    # addition needs this same treatment against a real migrated database.
    op.execute('''
ALTER TYPE subscriptionstatus ADD VALUE IF NOT EXISTS 'GRACE';
ALTER TYPE subscriptionstatus ADD VALUE IF NOT EXISTS 'SUSPENDED';
''')


def downgrade() -> None:
    # Postgres cannot drop a single enum value in place. Downgrading would
    # mean rebuilding the type and every column that uses it, which is not
    # worth doing for a value that (if this migration is being rolled back)
    # should not be in use yet. Left as a no-op, consistent with there being
    # no practical rollback for an additive enum change on this codebase.
    pass
