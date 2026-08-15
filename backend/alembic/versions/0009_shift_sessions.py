"""cash drawer sessions, and the shift a payment belongs to

Revision ID: 0009_shift_sessions
Revises: 0008_receipt_printing
Create Date: 2026-08-16
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_shift_sessions"
down_revision: Union[str, None] = "0008_receipt_printing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('''
CREATE TYPE shiftstatus AS ENUM ('OPEN', 'CLOSED');

CREATE TABLE shift_sessions (
	business_id UUID NOT NULL,
	status shiftstatus NOT NULL,
	opened_by_user_id UUID,
	opened_at TIMESTAMP WITH TIME ZONE NOT NULL,
	opening_float NUMERIC(10, 2) NOT NULL,
	closed_by_user_id UUID,
	closed_at TIMESTAMP WITH TIME ZONE,
	declared_cash NUMERIC(10, 2),
	expected_cash NUMERIC(10, 2),
	variance NUMERIC(10, 2),
	notes TEXT,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE,
	FOREIGN KEY(opened_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
	FOREIGN KEY(closed_by_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_shift_sessions_business_id ON shift_sessions (business_id);
CREATE INDEX ix_shift_sessions_status ON shift_sessions (status);
CREATE INDEX ix_shift_sessions_opened_by_user_id ON shift_sessions (opened_by_user_id);

-- One open drawer per cashier, enforced by the database rather than only by
-- the service. Two open shifts for the same person means every payment they
-- take has to guess which it belongs to, and a shortfall in one can always
-- be explained away as a surplus in the other. Partial, so closed shifts do
-- not collide with each other.
CREATE UNIQUE INDEX uq_one_open_shift_per_user
	ON shift_sessions (business_id, opened_by_user_id)
	WHERE status = 'OPEN' AND opened_by_user_id IS NOT NULL;

-- Nullable on both: money taken before shifts existed, or with no shift
-- open, still has to be recordable. A missing drawer must never block
-- taking payment.
ALTER TABLE payments
	ADD COLUMN shift_id UUID REFERENCES shift_sessions (id) ON DELETE SET NULL;
ALTER TABLE refunds
	ADD COLUMN shift_id UUID REFERENCES shift_sessions (id) ON DELETE SET NULL;

CREATE INDEX ix_payments_shift_id ON payments (shift_id);
CREATE INDEX ix_refunds_shift_id ON refunds (shift_id);
''')


def downgrade() -> None:
    op.execute('''
DROP INDEX IF EXISTS ix_refunds_shift_id;
DROP INDEX IF EXISTS ix_payments_shift_id;
ALTER TABLE refunds DROP COLUMN IF EXISTS shift_id;
ALTER TABLE payments DROP COLUMN IF EXISTS shift_id;
DROP TABLE IF EXISTS shift_sessions;
DROP TYPE IF EXISTS shiftstatus;
''')
