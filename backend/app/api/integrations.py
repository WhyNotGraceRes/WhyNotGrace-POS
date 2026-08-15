from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_business_id, require_feature, require_roles
from app.core.permissions import ROLE_FULL_ACCESS
from app.database.session import get_db
from app.database.transaction import transaction
from app.models.enums import FeatureModule, IntegrationProvider
from app.schemas.integration import ConnectCredentialsRequest, IntegrationOut
from app.services import audit_service, integration_service, menu_service

router = APIRouter(prefix="/integrations", tags=["integrations"])

_FEATURE_BY_PROVIDER = {
    IntegrationProvider.ZOMATO: FeatureModule.ZOMATO,
    IntegrationProvider.SWIGGY: FeatureModule.SWIGGY,
}


@router.get("", response_model=list[IntegrationOut])
def list_integrations(
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    _user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    out = []
    for integration in integration_service.list_integrations(db, business_id):
        item = IntegrationOut.model_validate(integration)
        if integration.is_connected:
            item.masked_key_id = integration_service.get_masked_key_id(db, business_id, integration.provider)
        out.append(item)
    return out


@router.put("/{provider}/credentials", response_model=IntegrationOut)
def connect_credentials(
    provider: IntegrationProvider,
    payload: ConnectCredentialsRequest,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    with transaction(db):
        integration = integration_service.connect_credentials(db, business_id, provider, payload.credentials)
        audit_service.record(
            db, action="integration.connect", business_id=business_id, user_id=user.id,
            resource_type="integration", resource_id=provider.value,
        )
    out = IntegrationOut.model_validate(integration)
    out.masked_key_id = integration_service.get_masked_key_id(db, business_id, provider)
    return out


@router.delete("/{provider}/credentials", response_model=IntegrationOut)
def disconnect(
    provider: IntegrationProvider,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    with transaction(db):
        integration = integration_service.disconnect(db, business_id, provider)
        audit_service.record(
            db, action="integration.disconnect", business_id=business_id, user_id=user.id,
            resource_type="integration", resource_id=provider.value,
        )
    return IntegrationOut.model_validate(integration)


@router.post("/{provider}/menu-sync", status_code=status.HTTP_202_ACCEPTED)
def sync_menu(
    provider: IntegrationProvider,
    business_id=Depends(get_current_business_id),
    db: Session = Depends(get_db),
    user=Depends(require_roles(*ROLE_FULL_ACCESS)),
):
    if provider not in _FEATURE_BY_PROVIDER:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Menu sync is not supported for this provider")

    from app.core.dependencies import require_feature_for_business

    require_feature_for_business(db, business_id, _FEATURE_BY_PROVIDER[provider])

    items = menu_service.list_items(db, business_id)
    menu_payload = {
        "items": [
            {"id": str(i.id), "name": i.name, "price": float(i.base_price), "is_active": i.is_active}
            for i in items
        ]
    }
    with transaction(db):
        integration_service.sync_menu(db, business_id, provider, menu_payload)
        audit_service.record(
            db, action="integration.menu_sync", business_id=business_id, user_id=user.id,
            resource_type="integration", resource_id=provider.value,
        )
    return {"status": "sync requested"}


@router.post("/webhooks/zomato", status_code=status.HTTP_200_OK)
async def zomato_webhook(request: Request, x_zomato_signature: str = Header(default="", alias="X-Zomato-Signature"), db: Session = Depends(get_db)):
    from app.models.enums import WebhookProcessStatus
    from app.models.integration import WebhookEvent
    from app.services.integrations.base import IntegrationNotConfigured
    from app.services.integrations.zomato_provider import zomato_provider

    raw_body = await request.body()
    try:
        valid = zomato_provider.verify_webhook_signature(raw_body=raw_body, signature=x_zomato_signature, credentials={})
    except IntegrationNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    with transaction(db):
        event = WebhookEvent(
            provider=IntegrationProvider.ZOMATO, provider_event_id=f"zomato-{hash(raw_body)}",
            signature_valid=valid, raw_payload=raw_body.decode("utf-8", errors="replace"),
            status=WebhookProcessStatus.PROCESSED if valid else WebhookProcessStatus.FAILED,
        )
        db.add(event)
    return {"received": True}


@router.post("/webhooks/swiggy", status_code=status.HTTP_200_OK)
async def swiggy_webhook(request: Request, x_swiggy_signature: str = Header(default="", alias="X-Swiggy-Signature"), db: Session = Depends(get_db)):
    from app.models.enums import WebhookProcessStatus
    from app.models.integration import WebhookEvent
    from app.services.integrations.base import IntegrationNotConfigured
    from app.services.integrations.swiggy_provider import swiggy_provider

    raw_body = await request.body()
    try:
        valid = swiggy_provider.verify_webhook_signature(raw_body=raw_body, signature=x_swiggy_signature, credentials={})
    except IntegrationNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    with transaction(db):
        event = WebhookEvent(
            provider=IntegrationProvider.SWIGGY, provider_event_id=f"swiggy-{hash(raw_body)}",
            signature_valid=valid, raw_payload=raw_body.decode("utf-8", errors="replace"),
            status=WebhookProcessStatus.PROCESSED if valid else WebhookProcessStatus.FAILED,
        )
        db.add(event)
    return {"received": True}
