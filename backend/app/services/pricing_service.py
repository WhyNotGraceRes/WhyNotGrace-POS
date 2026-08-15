"""Server-side price resolution. This is the ONLY place a price is
decided. Callers (order_service) must never accept a price from the
client — only item_id / variant_id / option_ids / pricing_context.
"""
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import PricingContext
from app.models.menu import MenuItem, MenuOption, MenuVariant
from app.models.pricing import PriceRule


def resolve_unit_price(
    db: Session,
    *,
    business_id: uuid.UUID,
    item: MenuItem,
    variant_id: uuid.UUID | None,
    context: PricingContext,
) -> float:
    """Resolve the base unit price (before options) for an item in a given
    pricing context. Precedence: PriceRule for (item, variant, context) >
    PriceRule for (item, None, context) > base_price (+ variant delta).
    """
    rule = (
        db.query(PriceRule)
        .filter(
            PriceRule.business_id == business_id,
            PriceRule.item_id == item.id,
            PriceRule.context == context,
            PriceRule.is_active.is_(True),
            PriceRule.variant_id == variant_id,
        )
        .first()
    )
    if rule is not None:
        return float(rule.price)

    if variant_id is not None:
        rule = (
            db.query(PriceRule)
            .filter(
                PriceRule.business_id == business_id,
                PriceRule.item_id == item.id,
                PriceRule.context == context,
                PriceRule.is_active.is_(True),
                PriceRule.variant_id.is_(None),
            )
            .first()
        )
        if rule is not None:
            variant = db.get(MenuVariant, variant_id)
            delta = float(variant.price_delta) if variant else 0.0
            return float(rule.price) + delta

    base = float(item.base_price)
    if variant_id is not None:
        variant = db.get(MenuVariant, variant_id)
        if variant is None or variant.item_id != item.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid variant for this item")
        base += float(variant.price_delta)
    return base


def resolve_unit_prices_bulk(
    db: Session, *, business_id: uuid.UUID, items: list[MenuItem], context: PricingContext
) -> dict[uuid.UUID, float]:
    """Batched equivalent of calling resolve_unit_price(..., variant_id=None)
    once per item — used only by the QR menu-listing endpoint
    (qr_service.build_menu_response), which needs every item's base display
    price in a single response and was issuing one PriceRule query per item
    (measured as the dominant N+1 pattern under load-test concurrency: a
    36-item menu issued ~36 extra round-trips per request, holding a pooled
    DB connection for the whole time). Order placement's per-line-item
    pricing keeps calling resolve_unit_price() directly and is unaffected —
    it prices a handful of cart lines, not an entire menu, so batching
    would add complexity with no measured benefit there.

    Only covers the variant_id=None case because that's the only way
    build_menu_response ever calls resolve_unit_price today; precedence
    (item-level PriceRule > base_price) is otherwise identical.
    """
    if not items:
        return {}
    item_ids = [item.id for item in items]
    rules = (
        db.query(PriceRule)
        .filter(
            PriceRule.business_id == business_id,
            PriceRule.item_id.in_(item_ids),
            PriceRule.context == context,
            PriceRule.is_active.is_(True),
            PriceRule.variant_id.is_(None),
        )
        .all()
    )
    rule_price_by_item_id = {rule.item_id: float(rule.price) for rule in rules}
    return {item.id: rule_price_by_item_id.get(item.id, float(item.base_price)) for item in items}


def resolve_option_price_deltas(
    db: Session, *, business_id: uuid.UUID, item_id: uuid.UUID, option_ids: list[uuid.UUID]
) -> list[MenuOption]:
    if not option_ids:
        return []
    options = (
        db.query(MenuOption)
        .join(MenuOption.group)
        .filter(
            MenuOption.business_id == business_id,
            MenuOption.id.in_(option_ids),
            MenuOption.is_active.is_(True),
        )
        .all()
    )
    found_ids = {o.id for o in options}
    missing = set(option_ids) - found_ids
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more selected options are invalid")
    for option in options:
        if option.group.item_id != item_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Selected option does not belong to this item"
            )
    return options


def compute_line_item(
    db: Session,
    *,
    business_id: uuid.UUID,
    item_id: uuid.UUID,
    variant_id: uuid.UUID | None,
    option_ids: list[uuid.UUID],
    quantity: int,
    context: PricingContext,
) -> dict:
    item = db.query(MenuItem).filter(MenuItem.id == item_id, MenuItem.business_id == business_id).first()
    if item is None or not item.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Menu item is not available")
    if item.is_sold_out:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{item.name} is sold out")

    unit_price = resolve_unit_price(db, business_id=business_id, item=item, variant_id=variant_id, context=context)
    options = resolve_option_price_deltas(db, business_id=business_id, item_id=item_id, option_ids=option_ids)
    unit_price += sum(float(o.price_delta) for o in options)

    return {
        "item": item,
        "unit_price": round(unit_price, 2),
        "line_total": round(unit_price * quantity, 2),
        "options": options,
    }
