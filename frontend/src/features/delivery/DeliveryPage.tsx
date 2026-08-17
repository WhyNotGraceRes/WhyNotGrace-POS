import { useTranslation } from "react-i18next";
import { AlertTriangle, MapPin, Phone, StickyNote, Truck } from "lucide-react";
import toast from "react-hot-toast";

import { PageHeader } from "@/components/PageHeader";
import { FreshnessIndicator } from "@/components/FreshnessIndicator";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { Select } from "@/components/ui/Select";
import { formatCurrency } from "@/lib/format";
import { parseApiError } from "@/api/errors";
import { useDeliveryOrders, useUpdateDeliveryStatus } from "@/features/delivery/hooks";
import { OrderStatusBadge } from "@/features/orders/components/OrderStatusBadge";
import type { DeliveryStatus } from "@/types/models";

/** Mirrors the backend's DELIVERY_STATUS_TRANSITIONS (app/services/order_service.py)
 * so staff are only ever offered a legal next status — the backend still
 * re-validates and rejects anything else with 400, this just avoids
 * showing a dead-end option in the UI. */
const DELIVERY_TRANSITIONS: Record<string, DeliveryStatus[]> = {
  PLACED: ["CONFIRMED", "CANCELLED"],
  CONFIRMED: ["PREPARING", "CANCELLED"],
  PREPARING: ["READY", "CANCELLED"],
  READY: ["OUT_FOR_DELIVERY", "CANCELLED"],
  OUT_FOR_DELIVERY: ["DELIVERED", "CANCELLED"],
  DELIVERED: [],
  CANCELLED: [],
};

export function DeliveryPage() {
  const { t } = useTranslation();
  const { data: orders, isLoading, isError, isFetching, dataUpdatedAt, refetch } = useDeliveryOrders();
  const updateStatus = useUpdateDeliveryStatus();

  const handleUpdate = (orderId: string, status: DeliveryStatus) => {
    updateStatus.mutate(
      { orderId, payload: { status } },
      {
        onSuccess: () => toast.success(t("deliveryStaff.statusUpdated")),
        onError: (err) => toast.error(parseApiError(err).message),
      }
    );
  };

  return (
    <div>
      <PageHeader
        title={t("nav.delivery")}
        subtitle={t("deliveryStaff.subtitle")}
        actions={
          orders ? (
            <FreshnessIndicator dataUpdatedAt={dataUpdatedAt} isFetching={isFetching} onRefresh={() => void refetch()} />
          ) : undefined
        }
      />

      {isLoading && (
        <div className="flex justify-center py-16">
          <Spinner className="text-brand-600" />
        </div>
      )}

      {isError && (
        <div className="flex flex-col items-center gap-2 py-16 text-danger-600">
          <AlertTriangle size={22} />
          <p className="text-sm font-medium">{t("deliveryStaff.loadError")}</p>
        </div>
      )}

      {!isLoading && !isError && (orders ?? []).length === 0 && (
        <div className="flex flex-col items-center gap-2 py-16 text-center text-slate-400">
          <Truck size={24} />
          <p className="text-sm">{t("deliveryStaff.empty")}</p>
        </div>
      )}

      {!isLoading && !isError && (orders ?? []).length > 0 && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {(orders ?? []).map((order) => {
            const currentStatus = (order.delivery_status ?? "PLACED") as DeliveryStatus;
            const nextOptions = DELIVERY_TRANSITIONS[currentStatus] ?? [];
            return (
              <Card key={order.id} className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-bold text-slate-900">{order.order_number}</p>
                  <OrderStatusBadge status={order.status} />
                </div>

                {order.customer && (
                  <p className="mt-1.5 text-sm text-slate-700">{order.customer.first_name}</p>
                )}
                {order.customer && (
                  <p className="flex items-center gap-1 text-xs text-slate-500">
                    <Phone size={11} /> {order.customer.mobile}
                  </p>
                )}
                {order.delivery_address && (
                  <p className="mt-1.5 flex items-start gap-1 text-xs text-slate-600">
                    <MapPin size={12} className="mt-0.5 shrink-0" /> {order.delivery_address}
                  </p>
                )}
                {order.delivery_instructions && (
                  <p className="mt-1 flex items-start gap-1 text-xs italic text-slate-400">
                    <StickyNote size={12} className="mt-0.5 shrink-0" /> {order.delivery_instructions}
                  </p>
                )}

                <ul className="mt-2 space-y-1">
                  {order.items.map((item) => (
                    <li key={item.id} className="text-xs text-slate-600">
                      {item.quantity} × {item.item_name_snapshot}
                    </li>
                  ))}
                </ul>
                {order.notes && <p className="mt-1.5 text-xs italic text-slate-400">"{order.notes}"</p>}
                <p className="mt-2 text-sm font-semibold text-slate-800">{formatCurrency(order.subtotal)}</p>

                <div className="mt-2 flex items-center gap-1.5 text-xs font-medium text-brand-700">
                  {t("deliveryStaff.currentStatus")}: {t(`deliveryStaff.status.${currentStatus}`)}
                </div>

                {nextOptions.length > 0 && (
                  <div className="mt-2">
                    <Select
                      defaultValue=""
                      onChange={(e) => {
                        const value = e.target.value as DeliveryStatus | "";
                        if (value) handleUpdate(order.id, value);
                        e.target.value = "";
                      }}
                      disabled={updateStatus.isPending}
                    >
                      <option value="" disabled>
                        {t("deliveryStaff.updateStatus")}
                      </option>
                      {nextOptions.map((s) => (
                        <option key={s} value={s}>
                          {t(`deliveryStaff.status.${s}`)}
                        </option>
                      ))}
                    </Select>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
