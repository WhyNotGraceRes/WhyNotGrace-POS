import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { Receipt } from "lucide-react";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { OrderStatusBadge } from "@/features/orders/components/OrderStatusBadge";
import { BillDetailDialog } from "@/features/billing/components/BillDetailDialog";
import { formatCurrency } from "@/lib/format";
import { parseApiError } from "@/api/errors";
import { useAuthStore } from "@/stores/authStore";
import { useCancelOrder } from "@/features/orders/hooks";
import { useServeKot } from "@/features/kitchen/hooks";
import { useGenerateBill } from "@/features/billing/hooks";
import type { KOTOut, LocationOut, OrderOut } from "@/types/models";

const SERVICE_ROLES = new Set(["OWNER", "MANAGER", "SERVICE_COUNTER"]);
const CANCEL_ROLES = new Set(["OWNER", "MANAGER"]);
const BILLING_ROLES = new Set(["OWNER", "MANAGER", "CASH_COUNTER"]);

export function OrderDetailDialog({
  order,
  tables,
  kots,
  onClose,
}: {
  order: OrderOut | null;
  tables: LocationOut[];
  kots: KOTOut[];
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const role = useAuthStore((s) => s.user?.role);
  const cancelOrder = useCancelOrder();
  const serveKot = useServeKot();
  const generateBill = useGenerateBill();
  const [billId, setBillId] = useState<string | null>(null);

  if (!order) return null;

  const table = tables.find((tb) => tb.id === order.location_id);
  const orderKots = kots.filter((k) => k.order_id === order.id);
  const canCancel = role && CANCEL_ROLES.has(role) && !["SERVED", "DELIVERED", "COMPLETED", "CANCELLED"].includes(order.status);
  const canServe = role && SERVICE_ROLES.has(role);
  const canBill = role && BILLING_ROLES.has(role);

  return (
    <Dialog open={Boolean(order)} onClose={onClose} title={order.order_number} size="lg">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <OrderStatusBadge status={order.status} />
        <span className="rounded-full bg-stone-100 px-2.5 py-0.5 text-xs font-semibold text-stone-600">
          {t(`orderSource.${order.source}`)}
        </span>
        {order.is_additional && (
          <span className="rounded-full bg-accent-100 px-2.5 py-0.5 text-xs font-semibold text-accent-700">
            {t("orders.additional")}
          </span>
        )}
        <span className="text-sm text-stone-500">{table?.name ?? "—"}</span>
      </div>

      <ul className="divide-y divide-stone-100 rounded-lg border border-stone-100">
        {order.items.map((item) => (
          <li key={item.id} className="p-3">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-stone-800">
                {item.quantity} × {item.item_name_snapshot}
              </span>
              <span className="font-semibold text-stone-800">{formatCurrency(item.line_total)}</span>
            </div>
            {item.options.length > 0 && (
              <p className="mt-0.5 text-xs text-stone-500">{item.options.map((o) => o.option_name_snapshot).join(", ")}</p>
            )}
            {item.special_instructions && (
              <p className="mt-0.5 text-xs italic text-stone-400">"{item.special_instructions}"</p>
            )}
          </li>
        ))}
      </ul>

      <div className="mt-3 flex items-center justify-between">
        <span className="text-sm font-semibold text-stone-600">{t("orders.subtotal")}</span>
        <span className="text-lg font-bold text-stone-900">{formatCurrency(order.subtotal)}</span>
      </div>

      {order.notes && (
        <p className="mt-3 rounded-lg bg-stone-50 p-3 text-sm text-stone-600">
          <span className="font-semibold">{t("orders.notes")}: </span>
          {order.notes}
        </p>
      )}

      {orderKots.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-500">{t("orders.kots")}</p>
          <ul className="space-y-2">
            {orderKots.map((kot) => (
              <li key={kot.id} className="flex items-center justify-between rounded-lg border border-stone-100 px-3 py-2 text-sm">
                <span className="font-medium text-stone-700">{kot.kot_number}</span>
                <span className="flex items-center gap-2">
                  <span className="text-xs font-semibold uppercase tracking-wide text-stone-500">
                    {t(`kotStatus.${kot.status}`)}
                  </span>
                  {kot.status === "READY" && canServe && (
                    <Button
                      size="sm"
                      variant="secondary"
                      isLoading={serveKot.isPending}
                      onClick={() =>
                        serveKot.mutate(kot.id, {
                          onSuccess: () => toast.success(t("orders.markedServed")),
                          onError: (err) => toast.error(parseApiError(err).message),
                        })
                      }
                    >
                      {t("orders.markServed")}
                    </Button>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {canBill && (
        <Button
          variant="secondary"
          className="mt-5 w-full"
          isLoading={generateBill.isPending}
          onClick={() =>
            generateBill.mutate(
              { session_id: order.session_id },
              {
                onSuccess: (bill) => setBillId(bill.id),
                onError: (err) => toast.error(parseApiError(err).message),
              }
            )
          }
        >
          <Receipt size={16} />
          {t("billing.viewBill")}
        </Button>
      )}

      {canCancel && (
        <Button
          variant="danger"
          className="mt-2 w-full"
          isLoading={cancelOrder.isPending}
          onClick={() =>
            cancelOrder.mutate(order.id, {
              onSuccess: () => {
                toast.success(t("orders.cancelled"));
                onClose();
              },
              onError: (err) => toast.error(parseApiError(err).message),
            })
          }
        >
          {t("orders.cancelOrder")}
        </Button>
      )}

      <BillDetailDialog billId={billId} tables={tables} source={order.source} onClose={() => setBillId(null)} />
    </Dialog>
  );
}
