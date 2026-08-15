import json
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.encryption import decrypt_text, encrypt_text
from app.models.enums import IntegrationProvider
from app.models.integration import Integration, IntegrationCredential, IntegrationLog
from app.services.integrations.base import IntegrationNotConfigured
from app.services.integrations.zomato_provider import zomato_provider
from app.services.integrations.swiggy_provider import swiggy_provider

_PROVIDER_MAP = {
    IntegrationProvider.ZOMATO: zomato_provider,
    IntegrationProvider.SWIGGY: swiggy_provider,
}


def get_or_create_integration(db: Session, business_id: uuid.UUID, provider: IntegrationProvider) -> Integration:
    integration = db.query(Integration).filter(
        Integration.business_id == business_id, Integration.provider == provider
    ).first()
    if integration is None:
        integration = Integration(business_id=business_id, provider=provider, is_connected=False)
        db.add(integration)
        db.flush()
    return integration


def list_integrations(db: Session, business_id: uuid.UUID) -> list[Integration]:
    return [get_or_create_integration(db, business_id, p) for p in IntegrationProvider]


def _get_credentials(db: Session, integration_id: uuid.UUID) -> dict:
    row = db.query(IntegrationCredential).filter(IntegrationCredential.integration_id == integration_id).first()
    if row is None:
        return {}
    return json.loads(decrypt_text(row.encrypted_payload))


def get_masked_key_id(db: Session, business_id: uuid.UUID, provider: IntegrationProvider) -> str | None:
    """Only key_id (never key_secret/webhook_secret) is ever surfaced, and
    only in masked form, for the settings UI to confirm which account is
    connected without exposing the full identifier.
    """
    creds = get_business_credentials(db, business_id, provider)
    key_id = creds.get("key_id")
    if not key_id:
        return None
    if len(key_id) <= 8:
        return "*" * len(key_id)
    return f"{key_id[:6]}{'*' * (len(key_id) - 10)}{key_id[-4:]}"


def get_business_credentials(db: Session, business_id: uuid.UUID, provider: IntegrationProvider) -> dict:
    """Public accessor for a connected integration's decrypted credentials,
    scoped to exactly one business. Returns {} if the business has never
    connected this provider (never a different business's credentials).
    """
    integration = db.query(Integration).filter(
        Integration.business_id == business_id, Integration.provider == provider, Integration.is_connected.is_(True)
    ).first()
    if integration is None:
        return {}
    return _get_credentials(db, integration.id)


def connect_credentials(db: Session, business_id: uuid.UUID, provider: IntegrationProvider, credentials: dict) -> Integration:
    integration = get_or_create_integration(db, business_id, provider)
    payload = encrypt_text(json.dumps(credentials))

    row = db.query(IntegrationCredential).filter(IntegrationCredential.integration_id == integration.id).first()
    if row is None:
        row = IntegrationCredential(integration_id=integration.id, encrypted_payload=payload)
        db.add(row)
    else:
        row.encrypted_payload = payload

    integration.is_connected = True
    db.flush()

    db.add(
        IntegrationLog(
            business_id=business_id, provider=provider, action="credentials.connect", success=True,
            detail="Credentials stored (encrypted).",
        )
    )
    db.flush()
    return integration


def disconnect(db: Session, business_id: uuid.UUID, provider: IntegrationProvider) -> Integration:
    integration = get_or_create_integration(db, business_id, provider)
    db.query(IntegrationCredential).filter(IntegrationCredential.integration_id == integration.id).delete()
    integration.is_connected = False
    db.flush()
    db.add(IntegrationLog(business_id=business_id, provider=provider, action="credentials.disconnect", success=True))
    db.flush()
    return integration


def sync_menu(db: Session, business_id: uuid.UUID, provider: IntegrationProvider, menu_payload: dict) -> None:
    integration = get_or_create_integration(db, business_id, provider)
    credentials = _get_credentials(db, integration.id)
    provider_impl = _PROVIDER_MAP[provider]

    try:
        result = provider_impl.sync_menu(credentials=credentials, menu_payload=menu_payload)
        db.add(
            IntegrationLog(
                business_id=business_id, provider=provider, action="menu.sync", success=True,
                detail=f"Synced {result.items_synced} items.",
            )
        )
        integration.is_connected = True
    except IntegrationNotConfigured as exc:
        # Commit (not just flush): the caller's `with transaction(db):`
        # rolls back on the HTTPException below, which would otherwise
        # discard this failure log entry.
        db.add(IntegrationLog(business_id=business_id, provider=provider, action="menu.sync", success=False, detail=str(exc)))
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    db.flush()
