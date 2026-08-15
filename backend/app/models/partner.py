"""Partner sales channels — first-party sites (a business's own ordering
website, e.g. a client site we built) that submit orders INTO WhyNotGrace.

Deliberately not modelled as an app.models.integration.Integration provider,
despite the surface similarity to Zomato/Swiggy. Those are *outbound*: we
call their API (sync_menu pushes our menu to them, push_order_status calls
them), and they are third parties whose platform we do not control. A
partner channel is the reverse direction — an inbound submitter — and the
trust model is different enough that sharing the table would mean one row
meaning two incompatible things.

Access is PROVISIONED, never self-serve. There is no registration endpoint:
a channel exists only because a business OWNER created it (see
app/api/partner_channels.py), and it can be revoked instantly. A site that
was never explicitly issued credentials by an owner has no way in.

Credential storage: the signing secret is Fernet-encrypted at rest via
app/core/encryption.py, the same mechanism used for Zomato/Swiggy/Razorpay
credentials. Hashing it instead was considered and rejected — HMAC
verification needs the same value the partner signs with, so the server
would have to sign with the stored hash, which makes the hash itself a
working credential and buys nothing over encryption. Encryption at least
means a dump of the table alone is not enough; the JWT_SECRET-derived key
is needed too.

The secret is still shown exactly once, at creation, and is never returned
by any endpoint afterwards. Losing it means rotating, not recovering.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PartnerChannel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One provisioned partner site, scoped to exactly one business.

    business_id here is the single source of truth for which tenant an
    inbound partner request may touch. It is resolved from the key_id on the
    request and never read from the payload — the same rule
    app/core/dependencies.py applies to the staff JWT.
    """

    __tablename__ = "partner_channels"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Human label chosen by the owner, e.g. "Sweet Home website".
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    # Public, non-secret identifier sent in the X-Partner-Key header. Unique
    # platform-wide so lookup needs no tenant hint from the caller — which
    # matters, because accepting a caller-supplied business id and then
    # verifying it is exactly the pattern that leads to tenant confusion.
    key_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    # The shared HMAC signing secret, Fernet-encrypted at rest (see
    # app/core/encryption.py). Never returned by any endpoint after the
    # single creation response.
    secret_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Which staff user provisioned this, for the audit trail.
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class PartnerMenuMap(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Maps a partner site's own item identifier to a real WhyNotGrace menu
    item (and optionally a specific variant).

    This table is what protects price integrity. A partner submits its own
    item reference — "sweet-home-paneer-tikka" — and the server looks up
    which menu item that is, then resolves the price through
    pricing_service exactly as every other channel does. Prices are never
    accepted from the request body, so a stolen key cannot buy a ₹460 dish
    for ₹1; the worst it can do is place a real order at the real price.

    An unmapped reference is rejected rather than guessed. Fuzzy-matching a
    partner's item name against the menu would be a silent way to charge for
    the wrong dish, so the mapping is required to be explicit.
    """

    __tablename__ = "partner_menu_maps"
    __table_args__ = (
        UniqueConstraint("channel_id", "external_ref", name="uq_partner_menu_map_channel_ref"),
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partner_channels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The identifier as the partner site knows it (their own slug/id).
    external_ref: Mapped[str] = mapped_column(String(200), nullable=False)

    menu_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_variants.id", ondelete="SET NULL"), nullable=True
    )


class PartnerRequestNonce(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Spent signature nonces, for replay rejection.

    A valid signed request captured off the wire could otherwise be resent
    verbatim to place the same order repeatedly. Each request carries a
    single-use nonce; recording it means the second presentation is refused
    even though its signature is genuine. The unique constraint is the
    actual enforcement — two concurrent replays race to insert, and the
    database rejects the loser rather than both passing a prior check.

    Rows are prunable: anything older than the signature freshness window
    (partner_signature_max_skew_seconds) can never be accepted again on
    timestamp grounds alone, so it no longer needs to be remembered.
    """

    __tablename__ = "partner_request_nonces"
    __table_args__ = (
        UniqueConstraint("channel_id", "nonce", name="uq_partner_nonce_channel_nonce"),
    )

    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partner_channels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nonce: Mapped[str] = mapped_column(String(128), nullable=False)
