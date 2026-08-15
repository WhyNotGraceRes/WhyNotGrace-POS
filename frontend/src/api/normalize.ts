/**
 * openapi-typescript marks Pydantic fields with a default (e.g.
 * `Field(default_factory=list)`) as optional, because they're absent from
 * the schema's `required` list — even though the backend always
 * serializes them (empty array when unset, never actually missing). These
 * helpers normalize that at the API boundary so every component downstream
 * can rely on plain arrays instead of repeating `?? []` everywhere.
 */
import type { BillOut, KOTOut, MenuItemOut, OrderOut } from "@/types/models";

export function normalizeMenuItem(item: MenuItemOut): MenuItemOut {
  return {
    ...item,
    variants: item.variants ?? [],
    option_groups: (item.option_groups ?? []).map((g) => ({ ...g, options: g.options ?? [] })),
  };
}

export function normalizeOrder(order: OrderOut): OrderOut {
  return {
    ...order,
    items: (order.items ?? []).map((item) => ({ ...item, options: item.options ?? [] })),
  };
}

export function normalizeKot(kot: KOTOut): KOTOut {
  return { ...kot, items: kot.items ?? [] };
}

export function normalizeBill(bill: BillOut): BillOut {
  return {
    ...bill,
    items: bill.items ?? [],
    taxes: bill.taxes ?? [],
    discounts: bill.discounts ?? [],
    service_charges: bill.service_charges ?? [],
  };
}
