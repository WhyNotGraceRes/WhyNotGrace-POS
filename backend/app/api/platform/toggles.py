import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.platform_dependencies import get_current_platform_user
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.platform_user import PlatformUser
from app.schemas.platform import PlatformToggleUpdateRequest
from app.schemas.toggle import ToggleOut
from app.services import audit_service, platform_service, toggle_service

router = APIRouter(prefix="/platform/businesses/{business_id}/toggles", tags=["platform-toggles"])


def _to_out(definition, enabled: bool, is_overridden: bool) -> ToggleOut:
    return ToggleOut(
        key=definition.key,
        group=definition.group,
        enabled=enabled,
        is_overridden=is_overridden,
        default=definition.default,
        owner_editable=definition.owner_editable,
        label=definition.label,
        description=definition.description,
        warning=definition.warning,
    )


@router.get("", response_model=list[ToggleOut])
def list_toggles(
    business_id: uuid.UUID,
    db: Session = Depends(get_db),
    _platform_user: PlatformUser = Depends(get_current_platform_user),
):
    platform_service.get_business_or_404(db, business_id)
    return [_to_out(d, enabled, overridden) for d, enabled, overridden in toggle_service.list_effective(db, business_id)]


@router.put("/{key}", response_model=ToggleOut)
def set_toggle(
    business_id: uuid.UUID,
    key: str,
    payload: PlatformToggleUpdateRequest,
    db: Session = Depends(get_db),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    """Can set any toggle, including owner_editable=False entitlements —
    see toggle_service.platform_set_toggle for why this is safe: the gate it
    skips exists to stop a business changing its own entitlements, not to
    stop the platform that grants them."""
    with transaction(db):
        platform_service.get_business_or_404(db, business_id)
        definition, enabled = toggle_service.platform_set_toggle(db, business_id, key, payload.enabled)
        audit_service.record(
            db, action="platform.toggle_update", business_id=business_id, platform_user_id=platform_user.id,
            resource_type="toggle", resource_id=key, metadata={"enabled": enabled},
        )
    return _to_out(definition, enabled, True)
