"""refunds, round-off, and refunded totals on the bill

Revision ID: 0007_refunds_and_round_off
Revises: 0006_invoice_integrity
Create Date: 2026-08-16

Makes the billing.allow_refunds and billing.round_off_total toggles real.
They were declared in the registry by 0006 but nothing read them, which is
worse than not shipping them — a switch that visibly does nothing teaches an
owner not to trust the others.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_refunds_and_round_off"
down_revision: Union[str, None] = "0006_invoice_integrity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('''
ALTER TABLE bills
	ADD COLUMN round_off NUMERIC(10, 2) NOT NULL DEFAULT 0,
	ADD COLUMN amount_refunded NUMERIC(10, 2) NOT NULL DEFAULT 0;

CREATE TABLE refunds (
	business_id UUID NOT NULL,
	bill_id UUID NOT NULL,
	payment_id UUID NOT NULL,
	amount NUMERIC(10, 2) NOT NULL,
	method paymentmethod NOT NULL,
	reason VARCHAR(255),
	notes TEXT,
	refunded_by_staff_id UUID,
	refunded_at TIMESTAMP WITH TIME ZONE NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_refund_amount_positive CHECK (amount > 0),
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE,
	FOREIGN KEY(bill_id) REFERENCES bills (id) ON DELETE CASCADE,
	-- RESTRICT, not CASCADE: a refund must not be able to outlive or be
	-- silently removed with the payment it reverses.
	FOREIGN KEY(payment_id) REFERENCES payments (id) ON DELETE RESTRICT,
	FOREIGN KEY(refunded_by_staff_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_refunds_business_id ON refunds (business_id);
CREATE INDEX ix_refunds_bill_id ON refunds (bill_id);
CREATE INDEX ix_refunds_payment_id ON refunds (payment_id);
''')


def downgrade() -> None:
    op.execute('''
DROP TABLE IF EXISTS refunds;

ALTER TABLE bills
	DROP COLUMN IF EXISTS round_off,
	DROP COLUMN IF EXISTS amount_refunded;
''')
