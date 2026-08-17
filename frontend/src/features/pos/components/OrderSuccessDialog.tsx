import { useTranslation } from "react-i18next";
import { CheckCircle2 } from "lucide-react";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { formatCurrency } from "@/lib/format";
import type { OrderOut } from "@/types/models";

/** Shows the SERVER-CONFIRMED order — order_number and every price here
 * come straight from the OrderOut the backend returned, not the cart's
 * pre-order estimate. */
export function OrderSuccessDialog({ order, onClose }: { order: OrderOut | null; onClose: () => void }) {
  const { t } = useTranslation();

  return (
    <Dialog
      open={Boolean(order)}
      onClose={onClose}
      title={t("pos.orderConfirmed")}
      footer={
        <Button className="w-full" onClick={onClose}>
          {t("pos.continueOrdering")}
        </Button>
      }
    >
      {order && (
        <div>
          <div className="mb-4 flex items-center gap-3 rounded-lg bg-success-50 p-3">
            <CheckCircle2 size={22} className="shrink-0 text-success-600" />
            <div>
              <p className="text-sm font-bold text-success-700">{order.order_number}</p>
              <p className="text-xs text-success-600">{t("pos.sentToKitchen")}</p>
            </div>
          </div>

          <ul className="divide-y divide-stone-100">
            {order.items.map((item) => (
              <li key={item.id} className="flex items-center justify-between py-2 text-sm">
                <span className="text-stone-700">
                  {item.quantity} × {item.item_name_snapshot}
                </span>
                <span className="font-semibold text-stone-800">{formatCurrency(item.line_total)}</span>
              </li>
            ))}
          </ul>

          <div className="mt-3 flex items-center justify-between border-t border-stone-100 pt-3">
            <span className="text-sm font-semibold text-stone-600">{t("pos.confirmedSubtotal")}</span>
            <span className="text-lg font-bold text-stone-900">{formatCurrency(order.subtotal)}</span>
          </div>
        </div>
      )}
    </Dialog>
  );
}
