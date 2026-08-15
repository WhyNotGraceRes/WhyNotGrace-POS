import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import IntegrationProvider, WebhookProcessStatus


class Integration(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One row per (business, provider). enabled follows the corresponding
    FeatureFlag; connected reflects whether valid credentials exist.
    """
    __tablename__ = "integrations"
    __table_args__ = (UniqueConstraint("business_id", "provider", name="uq_integration_business_provider"),)

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[IntegrationProvider] = mapped_column(nullable=False)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IntegrationCredential(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Encrypted-at-rest credential blob for a provider connection.
    Secrets are never returned via the API (see schemas/integrations.py).
    """
    __tablename__ = "integration_credentials"

    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integrations.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    encrypted_payload: Mapped[str] = mapped_column(Text, nullable=False)


class IntegrationEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Outbound/inbound domain events for a provider (menu sync requested,
    order ingested, status pushed, etc.) independent of raw webhook payloads.
    """
    __tablename__ = "integration_events"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[IntegrationProvider] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)


class WebhookEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Every inbound webhook is recorded here first (raw + signature) and
    deduplicated by (provider, provider_event_id) before being processed.
    """
    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_webhook_provider_event"),
    )

    business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=True, index=True
    )
    provider: Mapped[IntegrationProvider] = mapped_column(nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    signature_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[WebhookProcessStatus] = mapped_column(default=WebhookProcessStatus.RECEIVED, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class IntegrationLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "integration_logs"

    business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=True, index=True
    )
    provider: Mapped[IntegrationProvider] = mapped_column(nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
