import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MenuCategory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "menu_categories"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    items: Mapped[list["MenuItem"]] = relationship(back_populates="category", cascade="all, delete-orphan")


class MenuItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "menu_items"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    is_veg: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_sold_out: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_todays_special: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_specialty: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Which kitchen prints this item's ticket — "TANDOOR", "CHINESE",
    # "BAR". Free text rather than an enum: every kitchen divides itself
    # differently, and an enum would mean a migration per restaurant. NULL
    # means the default kitchen, so a business that never configures
    # stations keeps getting exactly one ticket per order.
    kitchen_station: Mapped[str | None] = mapped_column(String(50), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    category: Mapped["MenuCategory"] = relationship(back_populates="items")
    variants: Mapped[list["MenuVariant"]] = relationship(back_populates="item", cascade="all, delete-orphan")
    option_groups: Mapped[list["MenuOptionGroup"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )


class MenuVariant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """e.g. Half / Full size variants of the same item."""
    __tablename__ = "menu_variants"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "Half", "Full"
    price_delta: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    item: Mapped["MenuItem"] = relationship(back_populates="variants")


class MenuOptionGroup(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """e.g. 'Spice Level', 'Curry Type' — a configurable customization axis."""
    __tablename__ = "menu_option_groups"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_multiple: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    item: Mapped["MenuItem"] = relationship(back_populates="option_groups")
    options: Mapped[list["MenuOption"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class MenuOption(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """e.g. 'Extra Spicy', 'Black Curry', 'Large' — a single selectable
    option within a group. price_delta is added to the computed price.
    """
    __tablename__ = "menu_options"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_option_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price_delta: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    group: Mapped["MenuOptionGroup"] = relationship(back_populates="options")


class MenuAvailability(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Optional day/time window during which an item is orderable
    (e.g. breakfast-only items). Absence of a row means always available.
    """
    __tablename__ = "menu_availabilities"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Monday .. 6=Sunday
    start_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)  # minutes from midnight
    end_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
