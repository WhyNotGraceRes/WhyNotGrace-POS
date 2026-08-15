import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { Input } from "@/components/ui/Input";
import { formatCurrency } from "@/lib/format";
import { useAuthStore } from "@/stores/authStore";
import { useOrders } from "@/features/orders/hooks";
import { useTables } from "@/features/tables/hooks";
import { useRooms } from "@/features/rooms/hooks";
import { useIsFeatureEnabled } from "@/features/settings/hooks";
import { useKots } from "@/features/kot/hooks";
import { useReadyForService } from "@/features/kitchen/hooks";
import { OrderStatusBadge } from "@/features/orders/components/OrderStatusBadge";
import { OrderDetailDialog } from "@/features/orders/components/OrderDetailDialog";
import type { OrderOut, OrderStatus } from "@/types/models";

const STATUS_TABS: (OrderStatus | "ALL")[] = [
  "ALL",
  "PLACED",
  "CONFIRMED",
  "PREPARING",
  "READY",
  "SERVED",
  "COMPLETED",
  "CANCELLED",
];

export function OrdersPage() {
  const { t } = useTranslation();
  const role = useAuthStore((s) => s.user?.role);
  const [statusFilter, setStatusFilter] = useState<OrderStatus | "ALL">("ALL");
  const [search, setSearch] = useState("");
  const [selectedOrder, setSelectedOrder] = useState<OrderOut | null>(null);

  const { data: orders, isLoading, isError } = useOrders(
    statusFilter === "ALL" ? {} : { status_filter: statusFilter }
  );
  const hotelRoomsEnabled = useIsFeatureEnabled("HOTEL_ROOMS");
  const { data: tables } = useTables();
  const { data: rooms } = useRooms({ enabled: hotelRoomsEnabled });
  const locations = useMemo(() => [...(tables ?? []), ...(rooms ?? [])], [tables, rooms]);

  // KOT visibility follows the exact backend permission split: OWNER/MANAGER
  // hold ROLE_KITCHEN and can see the full KOT list; SERVICE_COUNTER only
  // holds ROLE_SERVICE and can see READY KOTs; CASH_COUNTER holds neither,
  // so no KOT endpoint is called for them at all (would just 403).
  const hasKitchenAccess = role === "OWNER" || role === "MANAGER";
  const hasServiceOnlyAccess = role === "SERVICE_COUNTER";
  const { data: fullKots } = useKots({}, { enabled: hasKitchenAccess });
  const { data: readyKots } = useReadyForService({ enabled: hasServiceOnlyAccess });
  const visibleKots = fullKots ?? readyKots ?? [];

  const tableName = (locationId: string | null) => locations.find((loc) => loc.id === locationId)?.name ?? "—";

  const rows = useMemo(() => {
    const all = orders ?? [];
    const query = search.trim().toLowerCase();
    if (!query) return all;
    return all.filter((order) => {
      const locationName = locations.find((loc) => loc.id === order.location_id)?.name ?? "";
      return order.order_number.toLowerCase().includes(query) || locationName.toLowerCase().includes(query);
    });
  }, [orders, search, locations]);

  return (
    <div>
      <PageHeader title={t("nav.orders")} />

      <div className="mb-4 max-w-xs">
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t("orders.searchPlaceholder")}
        />
      </div>

      <div className="mb-4 flex gap-2 overflow-x-auto pb-1">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setStatusFilter(tab)}
            className={
              "shrink-0 rounded-full px-3.5 py-1.5 text-sm font-semibold transition-colors focus-ring " +
              (statusFilter === tab ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200")
            }
          >
            {tab === "ALL" ? t("orders.all") : t(`orderStatus.${tab}`)}
          </button>
        ))}
      </div>

      <Card className="overflow-hidden">
        {isLoading && (
          <div className="flex justify-center py-16">
            <Spinner className="text-brand-600" />
          </div>
        )}

        {isError && (
          <div className="flex flex-col items-center gap-2 py-16 text-danger-600">
            <AlertTriangle size={22} />
            <p className="text-sm font-medium">{t("orders.loadError")}</p>
          </div>
        )}

        {!isLoading && !isError && rows.length === 0 && (
          <p className="py-16 text-center text-sm text-slate-400">
            {search ? t("orders.noSearchResults", { query: search }) : t("orders.empty")}
          </p>
        )}

        {!isLoading && !isError && rows.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <th className="px-4 py-3">{t("orders.orderNumber")}</th>
                  <th className="px-4 py-3">{t("orders.table")}</th>
                  <th className="px-4 py-3">{t("orders.source")}</th>
                  <th className="px-4 py-3">{t("orders.status")}</th>
                  <th className="px-4 py-3 text-right">{t("orders.subtotal")}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((order) => (
                  <tr
                    key={order.id}
                    onClick={() => setSelectedOrder(order)}
                    className="cursor-pointer border-b border-slate-50 hover:bg-slate-50"
                  >
                    <td className="px-4 py-3 font-medium text-slate-800">
                      {order.order_number}
                      {order.is_additional && (
                        <span className="ml-2 rounded-full bg-accent-100 px-2 py-0.5 text-[10px] font-semibold text-accent-700">
                          {t("orders.additional")}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{tableName(order.location_id)}</td>
                    <td className="px-4 py-3 text-slate-600">{t(`orderSource.${order.source}`)}</td>
                    <td className="px-4 py-3">
                      <OrderStatusBadge status={order.status} />
                    </td>
                    <td className="px-4 py-3 text-right font-semibold text-slate-800">
                      {formatCurrency(order.subtotal)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <OrderDetailDialog
        order={selectedOrder}
        tables={locations}
        kots={visibleKots}
        onClose={() => setSelectedOrder(null)}
      />
    </div>
  );
}
