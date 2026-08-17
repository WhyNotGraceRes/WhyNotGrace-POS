"""In-app notifications table — currently populated only when a customer
(not staff) places an order through QR ordering, pickup, delivery, or the
website checkout (see order_service.create_order / notification_service).

Revision ID: 0014_notifications
Revises: 0013_managed_subscription_plans
Create Date: 2026-08-17
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0014_notifications"
down_revision: Union[str, None] = "0013_managed_subscription_plans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('''
CREATE TABLE notifications (
	business_id UUID NOT NULL,
	type VARCHAR(40) NOT NULL,
	title VARCHAR(200) NOT NULL,
	body TEXT,
	resource_type VARCHAR(40),
	resource_id UUID,
	is_read BOOLEAN NOT NULL,
	read_at TIMESTAMP WITH TIME ZONE,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE
);

CREATE INDEX ix_notifications_business_id ON notifications (business_id);
CREATE INDEX ix_notifications_is_read ON notifications (is_read);
''')


def downgrade() -> None:
    op.execute('''
DROP TABLE IF EXISTS notifications;
''')
