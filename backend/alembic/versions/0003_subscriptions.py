"""platform subscription tables (subscriptions, subscription_payments)

Revision ID: 0003_subscriptions
Revises: 0002_menu_crud_and_delivery
Create Date: 2026-08-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_subscriptions"
down_revision: Union[str, None] = "0002_menu_crud_and_delivery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('''
CREATE TYPE subscriptionstatus AS ENUM ('PENDING', 'ACTIVE', 'PAYMENT_FAILED', 'CANCELLED', 'EXPIRED');

CREATE TABLE subscriptions (
	business_id UUID NOT NULL,
	plan_name VARCHAR(50) NOT NULL,
	amount NUMERIC(10, 2) NOT NULL,
	currency VARCHAR(8) NOT NULL,
	billing_interval VARCHAR(20) NOT NULL,
	status subscriptionstatus NOT NULL,
	current_period_start TIMESTAMP WITH TIME ZONE,
	current_period_end TIMESTAMP WITH TIME ZONE,
	cancelled_at TIMESTAMP WITH TIME ZONE,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_subscriptions_business UNIQUE (business_id),
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE
);
CREATE INDEX ix_subscriptions_business_id ON subscriptions (business_id);

CREATE TABLE subscription_payments (
	business_id UUID NOT NULL,
	subscription_id UUID NOT NULL,
	status paymentstatus NOT NULL,
	amount NUMERIC(10, 2) NOT NULL,
	currency VARCHAR(8) NOT NULL,
	provider VARCHAR(30),
	provider_order_id VARCHAR(120),
	provider_payment_id VARCHAR(120),
	provider_signature VARCHAR(255),
	verified_at TIMESTAMP WITH TIME ZONE,
	period_start TIMESTAMP WITH TIME ZONE,
	period_end TIMESTAMP WITH TIME ZONE,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE,
	FOREIGN KEY(subscription_id) REFERENCES subscriptions (id) ON DELETE CASCADE
);
CREATE INDEX ix_subscription_payments_business_id ON subscription_payments (business_id);
CREATE INDEX ix_subscription_payments_subscription_id ON subscription_payments (subscription_id);
CREATE INDEX ix_subscription_payments_provider_order_id ON subscription_payments (provider_order_id);
''')


def downgrade() -> None:
    op.execute('''
DROP TABLE IF EXISTS subscription_payments CASCADE;
DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TYPE IF EXISTS subscriptionstatus;
''')
