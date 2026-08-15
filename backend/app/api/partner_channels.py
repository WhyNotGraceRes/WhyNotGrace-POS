"""Owner-facing provisioning for partner sales channels.

There is intentionally no self-registration path anywhere in the system. A
partner site can only obtain credentials because an OWNER of a specific
business created them here, and the owner can revoke them here just as
directly. That is what keeps "reusable channel" from meaning "any third
party can connect": the mechanism is generic, the access is not.

Every route is ROLE_FULL_ACCESS (owner only) — not ROLE_OPERATIONAL —
because issuing a credential that can create orders is closer to adding a
staff member than to editing a menu.
"""
import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_roles
from app.core.permissions import ROLE_FULL_ACCESS
from app.database.session import get_db
from app.database.transaction import transaction
from app.schemas.partner import (
    PartnerChannelCreate,
    PartnerChannelOut,
    PartnerChannelWithSecretOut,
    PartnerMenuMapCreate,
    PartnerMenuMapOut,
)
from app.services import audit_service, partner_service

router = APIRouter(prefix="/partner-channels", tags=["partner-channels"])


@router.get("", response_model=list[PartnerChannelOut])
def list_channels(
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    return [PartnerChannelOut.model_validate(c) for c in partner_service.list_channels(db, business_id)]


@router.post("", response_model=PartnerChannelWithSecretOut, status_code=status.HTTP_201_CREATED)
def create_channel(
    payload: PartnerChannelCreate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    """Issues credentials. The response carries the signing secret, and it is
    the only time it is ever returned — see partner_service.create_channel."""
    with transaction(db):
        channel, secret = partner_service.create_channel(
            db, business_id, name=payload.name, created_by_user_id=user.id
        )
        audit_service.record(
            db, action="partner_channel.create", business_id=business_id, user_id=user.id,
            resource_type="partner_channel", resource_id=str(channel.id),
        )
    return PartnerChannelWithSecretOut(
        **PartnerChannelOut.model_validate(channel).model_dump(), secret=secret
    )


@router.post("/{channel_id}/rotate", response_model=PartnerChannelWithSecretOut)
def rotate_secret(
    channel_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    with transaction(db):
        channel, secret = partner_service.rotate_secret(db, business_id, channel_id)
        audit_service.record(
            db, action="partner_channel.rotate", business_id=business_id, user_id=user.id,
            resource_type="partner_channel", resource_id=str(channel.id),
        )
    return PartnerChannelWithSecretOut(
        **PartnerChannelOut.model_validate(channel).model_dump(), secret=secret
    )


@router.delete("/{channel_id}", response_model=PartnerChannelOut)
def revoke_channel(
    channel_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    """Revokes rather than deletes, so the audit trail and any orders already
    submitted through this channel stay attributable to it."""
    with transaction(db):
        channel = partner_service.revoke_channel(db, business_id, channel_id)
        audit_service.record(
            db, action="partner_channel.revoke", business_id=business_id, user_id=user.id,
            resource_type="partner_channel", resource_id=str(channel.id),
        )
    return PartnerChannelOut.model_validate(channel)


# ---------------------------------------------------------------------------
# Menu mapping
# ---------------------------------------------------------------------------

@router.get("/{channel_id}/menu-map", response_model=list[PartnerMenuMapOut])
def list_mappings(
    channel_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    return [PartnerMenuMapOut.model_validate(m) for m in partner_service.list_mappings(db, business_id, channel_id)]


@router.put("/{channel_id}/menu-map", response_model=PartnerMenuMapOut)
def upsert_mapping(
    channel_id: uuid.UUID,
    payload: PartnerMenuMapCreate,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    """Binds one of the partner's item refs to a real menu item. This is the
    owner-controlled half of price integrity: the partner chooses which ref
    to send, the owner chooses what that ref costs."""
    with transaction(db):
        mapping = partner_service.upsert_mapping(
            db, business_id, channel_id,
            external_ref=payload.external_ref,
            menu_item_id=payload.menu_item_id,
            variant_id=payload.variant_id,
        )
        audit_service.record(
            db, action="partner_channel.map_item", business_id=business_id, user_id=user.id,
            resource_type="partner_menu_map", resource_id=str(mapping.id),
        )
    return PartnerMenuMapOut.model_validate(mapping)


@router.delete("/{channel_id}/menu-map/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mapping(
    channel_id: uuid.UUID,
    mapping_id: uuid.UUID,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    with transaction(db):
        partner_service.delete_mapping(db, business_id, channel_id, mapping_id)
        audit_service.record(
            db, action="partner_channel.unmap_item", business_id=business_id, user_id=user.id,
            resource_type="partner_menu_map", resource_id=str(mapping_id),
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
