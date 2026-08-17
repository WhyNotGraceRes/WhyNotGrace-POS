import { useState } from "react";
import { useTranslation } from "react-i18next";
import { BedDouble, ChevronRight, Package, ShoppingCart, Trash2, Truck, UserRound, UtensilsCrossed, X } from "lucide-react";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/Button";
import { QuantityStepper } from "@/components/ui/QuantityStepper";
import { formatCurrency } from "@/lib/format";
import { cn } from "@/lib/cn";
import { parseApiError } from "@/api/errors";
import { cartEstimatedSubtotal, useCartStore, type OrderContext } from "@/stores/cartStore";
import { useCreateOrder } from "@/features/orders/hooks";
import { useIsFeatureEnabled } from "@/features/settings/hooks";
import { LocationSelectDialog } from "@/features/pos/components/LocationSelectDialog";
import { CustomerPickerDialog } from "@/features/customers/components/CustomerPickerDialog";
import type { OrderOut, OrderSource, PricingContext } from "@/types/models";

const CONTEXT_TABS: { context: OrderContext; icon: typeof UtensilsCrossed; labelKey: string }[] = [
  { context: "DINE_IN", icon: UtensilsCrossed, labelKey: "pos.context.dineIn" },
  { context: "ROOM_SERVICE", icon: BedDouble, labelKey: "pos.context.roomService" },
  { context: "PICKUP", icon: Package, labelKey: "pos.context.pickup" },
  { context: "DELIVERY", icon: Truck, labelKey: "pos.context.delivery" },
];

// Tailwind needs literal class names to pick them up at build time — an
// interpolated `grid-cols-${n}` string would never be generated.
const GRID_COLS_CLASS: Record<number, string> = {
  1: "grid-cols-1",
  2: "grid-cols-2",
  3: "grid-cols-3",
  4: "grid-cols-4",
};

export function CartPanel({ onOrderPlaced }: { onOrderPlaced: (order: OrderOut) => void }) {
  const { t } = useTranslation();
  const {
    orderContext,
    tableId,
    tableName,
    deliveryAddress,
    customerId,
    customerLabel,
    lines,
    setOrderContext,
    setTable,
    setDeliveryAddress,
    setCustomer,
    clearCustomer,
    setQuantity,
    removeLine,
    clearCart,
  } = useCartStore();
  const hotelRoomsEnabled = useIsFeatureEnabled("HOTEL_ROOMS");
  const pickupEnabled = useIsFeatureEnabled("PICKUP");
  const deliveryEnabled = useIsFeatureEnabled("DELIVERY");
  const createOrder = useCreateOrder();
  const [locationDialogOpen, setLocationDialogOpen] = useState(false);
  const [customerDialogOpen, setCustomerDialogOpen] = useState(false);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const visibleTabs = CONTEXT_TABS.filter((tab) => {
    if (tab.context === "ROOM_SERVICE") return hotelRoomsEnabled;
    if (tab.context === "PICKUP") return pickupEnabled;
    if (tab.context === "DELIVERY") return deliveryEnabled;
    return true;
  });

  const subtotal = cartEstimatedSubtotal(lines);
  const needsLocation = orderContext === "DINE_IN" || orderContext === "ROOM_SERVICE";
  const canPlaceOrder =
    lines.length > 0 &&
    (needsLocation ? Boolean(tableId) : orderContext === "DELIVERY" ? deliveryAddress.trim().length >= 5 : true);

  const handlePlaceOrder = async () => {
    if (!canPlaceOrder) return;
    setError(null);
    try {
      const order = await createOrder.mutateAsync({
        location_id: needsLocation ? tableId ?? undefined : undefined,
        source: orderContext as OrderSource,
        pricing_context: orderContext as PricingContext,
        delivery_address: orderContext === "DELIVERY" ? deliveryAddress.trim() : undefined,
        notes: notes.trim() || undefined,
        customer_id: customerId ?? undefined,
        items: lines.map((line) => ({
          menu_item_id: line.menuItemId,
          variant_id: line.variantId,
          quantity: line.quantity,
          option_ids: line.options.map((o) => o.id),
          special_instructions: line.specialInstructions,
        })),
      });
      clearCart();
      setNotes("");
      toast.success(t("pos.orderPlaced", { number: order.order_number }));
      onOrderPlaced(order);
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-stone-100 p-4">
        <h2 className="mb-2 text-sm font-bold text-stone-900">{t("pos.currentOrder")}</h2>

        <div className={cn("grid gap-1", GRID_COLS_CLASS[visibleTabs.length] ?? "grid-cols-4")}>
          {visibleTabs.map(({ context, icon: Icon, labelKey }) => (
            <button
              key={context}
              type="button"
              onClick={() => setOrderContext(context)}
              className={cn(
                "flex flex-col items-center gap-1 rounded-lg border px-1 py-1.5 text-[10px] font-semibold transition-colors focus-ring",
                orderContext === context ? "border-brand-500 bg-brand-50 text-brand-700" : "border-stone-200 text-stone-500 hover:bg-stone-50"
              )}
            >
              <Icon size={14} />
              {t(labelKey)}
            </button>
          ))}
        </div>

        {needsLocation && (
          <button
            type="button"
            onClick={() => setLocationDialogOpen(true)}
            className="mt-2 flex w-full items-center justify-between rounded-lg border border-stone-200 px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50 focus-ring"
          >
            <span>{tableName ?? (orderContext === "ROOM_SERVICE" ? t("pos.selectRoom") : t("pos.selectTable"))}</span>
            <ChevronRight size={16} className="text-stone-400" />
          </button>
        )}

        {orderContext === "DELIVERY" && (
          <textarea
            value={deliveryAddress}
            onChange={(e) => setDeliveryAddress(e.target.value)}
            placeholder={t("pos.deliveryAddressPlaceholder")}
            rows={2}
            maxLength={1000}
            className="mt-2 w-full rounded-lg border border-stone-300 px-3 py-1.5 text-sm focus-ring"
          />
        )}

        {orderContext === "PICKUP" && (
          <p className="mt-2 rounded-lg border border-dashed border-stone-200 px-3 py-2 text-xs text-stone-500">
            {t("pos.pickupHint")}
          </p>
        )}

        {customerLabel ? (
          <div className="mt-2 flex items-center justify-between rounded-lg border border-brand-200 bg-brand-50 px-3 py-2 text-sm">
            <span className="flex items-center gap-1.5 truncate text-brand-800">
              <UserRound size={14} />
              {customerLabel}
            </span>
            <button
              type="button"
              onClick={clearCustomer}
              className="shrink-0 text-brand-600 hover:text-brand-800"
              aria-label={t("customers.removeCustomer")}
            >
              <X size={14} />
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setCustomerDialogOpen(true)}
            className="mt-2 flex w-full items-center justify-between rounded-lg border border-dashed border-stone-200 px-3 py-2 text-sm font-medium text-stone-500 hover:bg-stone-50 focus-ring"
          >
            <span className="flex items-center gap-1.5">
              <UserRound size={14} />
              {t("customers.selectCustomer")}
            </span>
            <ChevronRight size={16} className="text-stone-400" />
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {lines.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-stone-400">
            <ShoppingCart size={28} />
            <p className="text-sm">{t("pos.cartEmpty")}</p>
          </div>
        ) : (
          <ul className="space-y-3">
            {lines.map((line) => (
              <li key={line.id} className="rounded-lg border border-stone-100 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-stone-800">{line.itemName}</p>
                    {line.variantName && <p className="text-xs text-stone-500">{line.variantName}</p>}
                    {line.options.length > 0 && (
                      <p className="text-xs text-stone-500">{line.options.map((o) => o.name).join(", ")}</p>
                    )}
                    {line.specialInstructions && (
                      <p className="mt-0.5 text-xs italic text-stone-400">"{line.specialInstructions}"</p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => removeLine(line.id)}
                    className="shrink-0 rounded-md p-1 text-stone-300 hover:bg-danger-50 hover:text-danger-500 focus-ring"
                    aria-label={t("pos.removeItem")}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                <div className="mt-2 flex items-center justify-between">
                  <QuantityStepper
                    size="sm"
                    value={line.quantity}
                    onChange={(q) => setQuantity(line.id, q)}
                    min={0}
                  />
                  <span className="text-sm font-bold text-stone-800">
                    {formatCurrency((line.unitEstimate + line.options.reduce((s, o) => s + o.priceDelta, 0)) * line.quantity)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="shrink-0 border-t border-stone-100 p-4">
        {lines.length > 0 && (
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder={t("pos.orderNotesPlaceholder")}
            rows={1}
            maxLength={1000}
            className="mb-3 w-full rounded-lg border border-stone-300 px-3 py-1.5 text-sm focus-ring"
          />
        )}

        {error && (
          <p className="mb-3 rounded-lg border border-danger-500/30 bg-danger-50 px-3 py-2 text-xs text-danger-700">
            {error}
          </p>
        )}

        <div className="mb-3 flex items-center justify-between">
          <span className="text-sm text-stone-500">{t("pos.estimatedSubtotal")}</span>
          <span className="text-lg font-bold text-stone-900">{formatCurrency(subtotal)}</span>
        </div>

        <Button
          size="lg"
          className="w-full"
          disabled={!canPlaceOrder}
          isLoading={createOrder.isPending}
          onClick={() => void handlePlaceOrder()}
        >
          {t("pos.placeOrder")}
        </Button>
      </div>

      <LocationSelectDialog
        open={locationDialogOpen}
        onClose={() => setLocationDialogOpen(false)}
        onSelect={setTable}
        mode={orderContext === "ROOM_SERVICE" ? "ROOM" : "TABLE"}
      />
      <CustomerPickerDialog
        open={customerDialogOpen}
        onClose={() => setCustomerDialogOpen(false)}
        onSelect={setCustomer}
      />
    </div>
  );
}
