"""platform_users and platform_refresh_tokens — WhyNotGrace's own staff,
a principal separate from any business's User (see app.models.platform_user
for why this is a separate table rather than a nullable business_id on User)

Revision ID: 0012_platform_users
Revises: 0011_complimentary_and_nc
Create Date: 2026-08-17
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012_platform_users"
down_revision: Union[str, None] = "0011_complimentary_and_nc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('''
CREATE TYPE platformrole AS ENUM ('SUPERADMIN');

CREATE TABLE platform_users (
	email VARCHAR(255) NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	first_name VARCHAR(100) NOT NULL,
	last_name VARCHAR(100) NOT NULL,
	role platformrole NOT NULL,
	is_active BOOLEAN NOT NULL,
	failed_login_attempts INTEGER NOT NULL DEFAULT 0,
	locked_until TIMESTAMP WITH TIME ZONE,
	last_login_at TIMESTAMP WITH TIME ZONE,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (email)
);
CREATE INDEX ix_platform_users_email ON platform_users (email);

CREATE TABLE platform_refresh_tokens (
	platform_user_id UUID NOT NULL,
	token_hash VARCHAR(64) NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	revoked_at TIMESTAMP WITH TIME ZONE,
	replaced_by_id UUID,
	user_agent VARCHAR(255),
	ip_address VARCHAR(64),
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (token_hash),
	FOREIGN KEY(platform_user_id) REFERENCES platform_users (id) ON DELETE CASCADE,
	FOREIGN KEY(replaced_by_id) REFERENCES platform_refresh_tokens (id) ON DELETE SET NULL
);
CREATE INDEX ix_platform_refresh_tokens_platform_user_id ON platform_refresh_tokens (platform_user_id);
CREATE INDEX ix_platform_refresh_tokens_token_hash ON platform_refresh_tokens (token_hash);

ALTER TABLE audit_logs
	ADD COLUMN platform_user_id UUID REFERENCES platform_users (id) ON DELETE SET NULL;
CREATE INDEX ix_audit_logs_platform_user_id ON audit_logs (platform_user_id);
''')


def downgrade() -> None:
    op.execute('''
DROP INDEX IF EXISTS ix_audit_logs_platform_user_id;
ALTER TABLE audit_logs DROP COLUMN IF EXISTS platform_user_id;

DROP TABLE IF EXISTS platform_refresh_tokens;
DROP TABLE IF EXISTS platform_users;
DROP TYPE IF EXISTS platformrole;
''')
