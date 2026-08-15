"""Per-business overrides for the fine-grained switches in
app/core/toggles.py.

Only overrides live here. A business with no row for a key uses the
registry's default, so this table stays small and a changed default in code
reaches every business that never expressed a preference. The alternative —
writing every toggle for every business at signup — would mean a new switch
needs a backfill before it works, and a changed default would silently not
apply to anyone.

The key is a plain string rather than an enum precisely so that adding a
switch costs no migration. Unknown keys are rejected at the API layer
against the registry, so the looseness here does not become a way to write
arbitrary rows.
"""
import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BusinessToggle(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "business_toggles"
    __table_args__ = (
        UniqueConstraint("business_id", "key", name="uq_business_toggle_key"),
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
