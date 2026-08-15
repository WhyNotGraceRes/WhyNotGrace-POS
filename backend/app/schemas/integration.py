import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import IntegrationProvider


class IntegrationOut(BaseModel):
    provider: IntegrationProvider
    is_connected: bool
    last_synced_at: datetime | None
    # Razorpay's key_id is a public identifier (the same value the
    # Razorpay Checkout widget uses client-side), so a masked form is safe
    # to show for at-a-glance confirmation. key_secret/webhook_secret are
    # never included anywhere in this schema.
    masked_key_id: str | None = None

    model_config = {"from_attributes": True}


class ConnectCredentialsRequest(BaseModel):
    """Free-form credential payload (e.g. client_id/client_secret/access_token).
    Encrypted at rest; never echoed back via the API.
    """
    credentials: dict[str, str]


class MenuSyncRequest(BaseModel):
    pass
