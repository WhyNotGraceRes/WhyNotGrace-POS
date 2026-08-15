"""partner sales channels (provisioned first-party sites submitting orders)

Revision ID: 0004_partner_channels
Revises: 0003_subscriptions
Create Date: 2026-08-15

Also adds the uniqueness that makes app.models.payment.IdempotencyKey
actually idempotent under concurrency. It was created in 0001 with only
non-unique indexes, so two simultaneous retries of the same request could
both find no existing row and both proceed. Partner order submission relies
on that table to make network retries safe, so the constraint is added here
rather than left as a latent race for every existing caller too.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_partner_channels"
down_revision: Union[str, None] = "0003_subscriptions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # FeatureModule is a real Postgres ENUM type, so adding a member to the
    # Python enum is not enough — the database type has to learn the value
    # too, or every read/write of the new flag fails with
    # "invalid input value for enum featuremodule".
    #
    # Worth knowing: the test suite cannot catch this. tests/conftest.py
    # builds the schema with Base.metadata.create_all(), which generates the
    # enum from whatever the Python enum currently says, so tests pass while
    # a migrated database breaks. Any future FeatureModule addition needs
    # this line too.
    #
    # ALTER TYPE ... ADD VALUE is allowed inside a transaction from
    # PostgreSQL 12 onward as long as the new value is not *used* in the same
    # transaction; nothing here inserts a PARTNER_CHANNEL row, so this is safe
    # under Alembic's transactional DDL.
    op.execute("ALTER TYPE featuremodule ADD VALUE IF NOT EXISTS 'PARTNER_CHANNEL';")

    op.execute('''
CREATE TABLE partner_channels (
	business_id UUID NOT NULL,
	name VARCHAR(120) NOT NULL,
	key_id VARCHAR(64) NOT NULL,
	secret_encrypted VARCHAR(512) NOT NULL,
	is_active BOOLEAN NOT NULL,
	revoked_at TIMESTAMP WITH TIME ZONE,
	last_used_at TIMESTAMP WITH TIME ZONE,
	created_by_user_id UUID,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE,
	FOREIGN KEY(created_by_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX ix_partner_channels_key_id ON partner_channels (key_id);
CREATE INDEX ix_partner_channels_business_id ON partner_channels (business_id);

CREATE TABLE partner_menu_maps (
	business_id UUID NOT NULL,
	channel_id UUID NOT NULL,
	external_ref VARCHAR(200) NOT NULL,
	menu_item_id UUID NOT NULL,
	variant_id UUID,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_partner_menu_map_channel_ref UNIQUE (channel_id, external_ref),
	FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE CASCADE,
	FOREIGN KEY(channel_id) REFERENCES partner_channels (id) ON DELETE CASCADE,
	FOREIGN KEY(menu_item_id) REFERENCES menu_items (id) ON DELETE CASCADE,
	FOREIGN KEY(variant_id) REFERENCES menu_variants (id) ON DELETE SET NULL
);

CREATE INDEX ix_partner_menu_maps_business_id ON partner_menu_maps (business_id);
CREATE INDEX ix_partner_menu_maps_channel_id ON partner_menu_maps (channel_id);
CREATE INDEX ix_partner_menu_maps_menu_item_id ON partner_menu_maps (menu_item_id);

CREATE TABLE partner_request_nonces (
	channel_id UUID NOT NULL,
	nonce VARCHAR(128) NOT NULL,
	id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_partner_nonce_channel_nonce UNIQUE (channel_id, nonce),
	FOREIGN KEY(channel_id) REFERENCES partner_channels (id) ON DELETE CASCADE
);

CREATE INDEX ix_partner_request_nonces_channel_id ON partner_request_nonces (channel_id);
CREATE INDEX ix_partner_request_nonces_created_at ON partner_request_nonces (created_at);
''')

    # Make idempotency_keys genuinely unique. Duplicates should not exist —
    # nothing has ever written the same (business_id, scope, key) twice on
    # purpose — but a pre-existing deployment could have raced one in, and a
    # migration that aborts halfway through is worse than one that resolves
    # the ambiguity deterministically. Keep the earliest row of each group,
    # which is the one whose resource_id callers were already given.
    op.execute('''
DELETE FROM idempotency_keys a
USING idempotency_keys b
WHERE a.id <> b.id
  AND a.scope = b.scope
  AND a.key = b.key
  AND a.business_id IS NOT DISTINCT FROM b.business_id
  AND a.created_at > b.created_at;

CREATE UNIQUE INDEX uq_idempotency_keys_business_scope_key
    ON idempotency_keys (business_id, scope, key);
''')


def downgrade() -> None:
    # The PARTNER_CHANNEL enum member is deliberately left in place.
    # PostgreSQL has no ALTER TYPE ... DROP VALUE, so removing it would mean
    # rebuilding the type and every column that uses it — a far riskier
    # operation than leaving an unused label behind, which costs nothing.
    op.execute('''
-- Compared as text rather than as the enum literal: if this downgrade runs
-- against a database where the ADD VALUE above never took effect, parsing
-- 'PARTNER_CHANNEL' as featuremodule would itself raise and abort the whole
-- downgrade. Casting the column sidesteps that and works either way.
DELETE FROM feature_flags WHERE module::text = 'PARTNER_CHANNEL';

DROP INDEX IF EXISTS uq_idempotency_keys_business_scope_key;
DROP TABLE IF EXISTS partner_request_nonces;
DROP TABLE IF EXISTS partner_menu_maps;
DROP TABLE IF EXISTS partner_channels;
''')
