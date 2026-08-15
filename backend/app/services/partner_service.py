"""Partner sales channels: provisioning, menu mapping, and order intake.

Two audiences in one module, deliberately kept together because the safety
argument spans both: what an owner is allowed to provision determines what a
partner is able to do.

The single most important rule here is that a partner submits *references*,
never prices. External refs are translated to real menu items through
PartnerMenuMap and then priced by pricing_service exactly like every other
channel, so the platform-wide invariant — "prices are only ever resolved
server-side" — holds for this channel too. See submit_order.
"""
import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.encryption import encrypt_text
from app.core.security import generate_url_safe_token
from app.models.enums import OrderSource, PricingContext
from app.models.menu import MenuItem, MenuVariant
from app.models.partner import PartnerChannel, PartnerMenuMap
from app.models.payment import IdempotencyKey
from app.services import order_service

IDEMPOTENCY_SCOPE = "partner_order"


# ---------------------------------------------------------------------------
# Provisioning (owner-facing)
# ---------------------------------------------------------------------------

def create_channel(db: Session, business_id: uuid.UUID, *, name: str, created_by_user_id: uuid.UUID) -> tuple[PartnerChannel, str]:
    """Issues a new channel. Returns (channel, plaintext_secret).

    The plaintext secret exists only in this return value — it is encrypted
    before storage and never read back out by any endpoint, so the caller
    must surface it to the owner now or not at all. That is the intended
    trade: a secret that can be re-displayed on demand is one that leaks
    through every future screen, log, and support conversation that touches
    it.
    """
    key_id = f"wng_{generate_url_safe_token(12)}"
    secret = generate_url_safe_token(32)
    channel = PartnerChannel(
        business_id=business_id,
        name=name,
        key_id=key_id,
        secret_encrypted=encrypt_text(secret),
        is_active=True,
        created_by_user_id=created_by_user_id,
    )
    db.add(channel)
    db.flush()
    return channel, secret


def list_channels(db: Session, business_id: uuid.UUID) -> list[PartnerChannel]:
    return (
        db.query(PartnerChannel)
        .filter(PartnerChannel.business_id == business_id)
        .order_by(PartnerChannel.created_at.desc())
        .all()
    )


def get_channel_or_404(db: Session, business_id: uuid.UUID, channel_id: uuid.UUID) -> PartnerChannel:
    channel = (
        db.query(PartnerChannel)
        .filter(PartnerChannel.id == channel_id, PartnerChannel.business_id == business_id)
        .first()
    )
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner channel not found")
    return channel


def rotate_secret(db: Session, business_id: uuid.UUID, channel_id: uuid.UUID) -> tuple[PartnerChannel, str]:
    """Replaces the signing secret. The old secret stops working the instant
    this commits — there is no overlap window, because a rotation is usually
    a response to suspected exposure and a grace period would keep the
    exposed credential alive exactly when it must not be."""
    channel = get_channel_or_404(db, business_id, channel_id)
    secret = generate_url_safe_token(32)
    channel.secret_encrypted = encrypt_text(secret)
    db.flush()
    return channel, secret


def revoke_channel(db: Session, business_id: uuid.UUID, channel_id: uuid.UUID) -> PartnerChannel:
    """The kill switch. Takes effect on the next request — authentication
    reads is_active/revoked_at on every call rather than caching channel
    state, so there is no window where a revoked key still works."""
    channel = get_channel_or_404(db, business_id, channel_id)
    channel.is_active = False
    channel.revoked_at = datetime.now(timezone.utc)
    db.flush()
    return channel


# ---------------------------------------------------------------------------
# Menu mapping (owner-facing)
# ---------------------------------------------------------------------------

def list_mappings(db: Session, business_id: uuid.UUID, channel_id: uuid.UUID) -> list[PartnerMenuMap]:
    get_channel_or_404(db, business_id, channel_id)
    return (
        db.query(PartnerMenuMap)
        .filter(PartnerMenuMap.business_id == business_id, PartnerMenuMap.channel_id == channel_id)
        .order_by(PartnerMenuMap.external_ref)
        .all()
    )


def upsert_mapping(
    db: Session,
    business_id: uuid.UUID,
    channel_id: uuid.UUID,
    *,
    external_ref: str,
    menu_item_id: uuid.UUID,
    variant_id: uuid.UUID | None,
) -> PartnerMenuMap:
    """Points one of the partner's item refs at a real menu item.

    Both the item and the variant are re-checked against this business —
    a mapping is the one place where an owner could otherwise attach another
    tenant's menu item to their own channel, so the ownership check happens
    here rather than being assumed from the channel alone.
    """
    get_channel_or_404(db, business_id, channel_id)

    item = (
        db.query(MenuItem)
        .filter(MenuItem.id == menu_item_id, MenuItem.business_id == business_id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown menu item for this business")

    if variant_id is not None:
        variant = (
            db.query(MenuVariant)
            .filter(MenuVariant.id == variant_id, MenuVariant.menu_item_id == menu_item_id)
            .first()
        )
        if variant is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Variant does not belong to the given menu item",
            )

    existing = (
        db.query(PartnerMenuMap)
        .filter(PartnerMenuMap.channel_id == channel_id, PartnerMenuMap.external_ref == external_ref)
        .first()
    )
    if existing is not None:
        existing.menu_item_id = menu_item_id
        existing.variant_id = variant_id
        db.flush()
        return existing

    mapping = PartnerMenuMap(
        business_id=business_id,
        channel_id=channel_id,
        external_ref=external_ref,
        menu_item_id=menu_item_id,
        variant_id=variant_id,
    )
    db.add(mapping)
    db.flush()
    return mapping


def delete_mapping(db: Session, business_id: uuid.UUID, channel_id: uuid.UUID, mapping_id: uuid.UUID) -> None:
    mapping = (
        db.query(PartnerMenuMap)
        .filter(
            PartnerMenuMap.id == mapping_id,
            PartnerMenuMap.channel_id == channel_id,
            PartnerMenuMap.business_id == business_id,
        )
        .first()
    )
    if mapping is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    db.delete(mapping)
    db.flush()


# ---------------------------------------------------------------------------
# Order intake (partner-facing)
# ---------------------------------------------------------------------------

class _ResolvedLine:
    """Mirrors the attribute shape order_service.create_order expects from a
    request schema, so partner orders travel the same code path as every
    other channel instead of a parallel one that could drift."""

    __slots__ = ("menu_item_id", "variant_id", "quantity", "option_ids", "special_instructions")

    def __init__(self, menu_item_id, variant_id, quantity, option_ids, special_instructions):
        self.menu_item_id = menu_item_id
        self.variant_id = variant_id
        self.quantity = quantity
        self.option_ids = option_ids
        self.special_instructions = special_instructions


def _resolve_lines(db: Session, channel: PartnerChannel, items) -> list[_ResolvedLine]:
    """Translates the partner's own refs into real menu items.

    An unknown ref is a hard 400. The tempting alternative — matching on
    name, or falling back to some default — would mean a typo on the partner
    side silently charges a guest for a different dish, which is a worse
    outcome than a rejected order that someone has to go fix.
    """
    refs = [line.external_ref for line in items]
    mappings = {
        m.external_ref: m
        for m in db.query(PartnerMenuMap).filter(
            PartnerMenuMap.channel_id == channel.id,
            PartnerMenuMap.external_ref.in_(refs),
        )
    }

    unknown = sorted({ref for ref in refs if ref not in mappings})
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "These items are not mapped to a menu item for this channel: "
                + ", ".join(unknown)
                + ". Map them before submitting orders that include them."
            ),
        )

    resolved = []
    for line in items:
        mapping = mappings[line.external_ref]
        resolved.append(
            _ResolvedLine(
                menu_item_id=mapping.menu_item_id,
                # A variant fixed by the mapping wins over anything the
                # request suggests; the mapping is owner-controlled, the
                # request is not.
                variant_id=mapping.variant_id,
                quantity=line.quantity,
                option_ids=[],
                special_instructions=line.special_instructions,
            )
        )
    return resolved


def _replay_existing_order(db: Session, business_id: uuid.UUID, idempotency_key: str):
    record = (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.business_id == business_id,
            IdempotencyKey.scope == IDEMPOTENCY_SCOPE,
            IdempotencyKey.key == idempotency_key,
        )
        .first()
    )
    if record is None or record.resource_id is None:
        return None
    return order_service.get_order_or_404(db, business_id, record.resource_id)


def submit_order(db: Session, channel: PartnerChannel, payload):
    """Creates a real order from a partner submission.

    business_id comes from the authenticated channel, never the payload.
    Prices are never read from the payload either — only quantities and item
    refs are, and pricing_service resolves the rest. The most a valid but
    hostile submission can do is order real food at real prices.

    Idempotency is keyed on (business_id, scope, client key): a partner
    retrying after a timeout gets the same order back rather than a second
    one. The unique index added in migration 0004 is what makes that safe
    when two retries arrive at once — the loser of the insert race re-reads
    the winner's order instead of creating its own.
    """
    if payload.idempotency_key:
        existing = _replay_existing_order(db, channel.business_id, payload.idempotency_key)
        if existing is not None:
            return existing, True

    lines = _resolve_lines(db, channel, payload.items)

    context = (
        PricingContext.DELIVERY
        if payload.fulfilment == "DELIVERY"
        else PricingContext.PICKUP
    )
    source = OrderSource.DELIVERY if payload.fulfilment == "DELIVERY" else OrderSource.PICKUP

    order = order_service.create_order(
        db,
        business_id=channel.business_id,
        location_id=None,
        source=source,
        pricing_context=context,
        items_payload=lines,
        notes=payload.notes,
        delivery_address=payload.delivery_address,
        delivery_instructions=payload.delivery_instructions,
        # Held exactly like a normal pickup/delivery order: the kitchen is
        # not told to start cooking until payment is settled. A partner site
        # asserting "this is paid" is not evidence of payment.
        hold_kot=True,
    )

    if payload.idempotency_key:
        db.add(
            IdempotencyKey(
                business_id=channel.business_id,
                scope=IDEMPOTENCY_SCOPE,
                key=payload.idempotency_key,
                resource_id=order.id,
                response_snapshot=json.dumps({"order_number": order.order_number}),
            )
        )
        try:
            db.flush()
        except IntegrityError:
            # A concurrent retry won the race. Its order is the canonical
            # one; return that rather than surfacing a conflict the partner
            # cannot act on.
            db.rollback()
            existing = _replay_existing_order(db, channel.business_id, payload.idempotency_key)
            if existing is not None:
                return existing, True
            raise

    return order, False
