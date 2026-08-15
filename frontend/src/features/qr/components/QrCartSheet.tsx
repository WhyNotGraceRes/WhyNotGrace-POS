import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ShoppingCart, Trash2 } from "lucide-react";

import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { QuantityStepper } from "@/components/ui/QuantityStepper";
import { formatCurrency } from "@/lib/format";
import { parseApiError } from "@/api/errors";
import { qrCartEstimatedSubtotal, useQrCartStore } from "@/stores/qrCartStore";
import { usePlaceQrOrder } from "@/features/qr/hooks";
import type { OrderOut } from "@/types/models";

export function QrCartSheet({
  open,
  onClose,
  sessionToken,
  onOrderPlaced,
}: {
  open: boolean;
  onClose: () => void;
  sessionToken: string;
  onOrderPlaced: (order: OrderOut) => void;
}) {
  const { t } = useTranslation();
  const { lines, setQuantity, removeLine, clearCart } = useQrCartStore();
  const placeOrder = usePlaceQrOrder();
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const subtotal = qrCartEstimatedSubtotal(lines);

  const handlePlaceOrder = async () => {
    if (lines.length === 0) return;
    setError(null);
    try {
      const order = await placeOrder.mutateAsync({
        sessionToken,
        payload: {
          notes: notes.trim() || undefined,
          items: lines.map((line) => ({
            menu_item_id: line.menuItemId,
            variant_id: line.variantId,
            quantity: line.quantity,
            option_ids: line.options.map((o) => o.id),
            special_instructions: line.specialInstructions,
          })),
        },
      });
      clearCart();
      setNotes("");
      onOrderPlaced(order);
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title={t("qr.cart.title")} size="sm">
      <div className="-mx-5 -my-4 flex h-[70vh] flex-col">
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {lines.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-slate-400">
              <ShoppingCart size={28} />
              <p className="text-sm">{t("qr.cart.empty")}</p>
            </div>
          ) : (
            <ul className="space-y-3">
              {lines.map((line) => (
                <li key={line.id} className="rounded-lg border border-slate-100 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-800">{line.itemName}</p>
                      {line.variantName && <p className="text-xs text-slate-500">{line.variantName}</p>}
                      {line.options.length > 0 && (
                        <p className="text-xs text-slate-500">{line.options.map((o) => o.name).join(", ")}</p>
                      )}
                      {line.specialInstructions && (
                        <p className="mt-0.5 text-xs italic text-slate-400">"{line.specialInstructions}"</p>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => removeLine(line.id)}
                      className="shrink-0 rounded-md p-1 text-slate-300 hover:bg-danger-50 hover:text-danger-500 focus-ring"
                      aria-label={t("pos.removeItem")}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <QuantityStepper size="sm" value={line.quantity} onChange={(q) => setQuantity(line.id, q)} min={0} />
                    <span className="text-sm font-bold text-slate-800">
                      {formatCurrency(
                        (line.unitEstimate + line.options.reduce((s, o) => s + o.priceDelta, 0)) * line.quantity
                      )}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="shrink-0 border-t border-slate-100 px-5 py-4">
          {lines.length > 0 && (
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={t("qr.cart.notesPlaceholder")}
              rows={1}
              maxLength={1000}
              className="mb-3 w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus-ring"
            />
          )}

          {error && (
            <p className="mb-3 rounded-lg border border-danger-500/30 bg-danger-50 px-3 py-2 text-xs text-danger-700">
              {error}
            </p>
          )}

          <div className="mb-3 flex items-center justify-between">
            <span className="text-sm text-slate-500">{t("pos.estimatedSubtotal")}</span>
            <span className="text-lg font-bold text-slate-900">{formatCurrency(subtotal)}</span>
          </div>

          <Button
            size="lg"
            className="w-full"
            disabled={lines.length === 0}
            isLoading={placeOrder.isPending}
            onClick={() => void handlePlaceOrder()}
          >
            {t("qr.cart.placeOrder")}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
