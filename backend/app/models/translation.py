import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Translation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Generic localized-content table. One row = one translated field on
    one entity in one language. This avoids duplicating backend logic or
    tables per language (see requirement: multi-language support without
    per-language schema duplication).

    entity_type: e.g. "menu_item", "menu_category", "website_config"
    entity_id:   PK of the row being translated
    field_name:  e.g. "name", "description", "story"
    language:    ISO code, e.g. "en", "hi", "mr"
    """
    __tablename__ = "translations"
    __table_args__ = (
        UniqueConstraint(
            "business_id", "entity_type", "entity_id", "field_name", "language",
            name="uq_translation_entity_field_lang",
        ),
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(60), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
