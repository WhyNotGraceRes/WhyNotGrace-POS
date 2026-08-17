import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { AlertTriangle, Receipt } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { FreshnessIndicator } from "@/components/FreshnessIndicator";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { parseApiError } from "@/api/errors";
import { useTables } from "@/features/tables/hooks";
import { useRooms } from "@/features/rooms/hooks";
import { useIsFeatureEnabled } from "@/features/settings/hooks";
import { useGenerateBill, useUnbilledOrders } from "@/features/billing/hooks";
import { BillDetailDialog } from "@/features/billing/components/BillDetailDialog";
import type { OrderOut } from "@/types/models";

/**
 * The backend has no "list all bills" endpoint (only POST /billing/generate,
 * which is an idempotent get-or-create by session_id, and GET /billing/{id}
 * by id — see backend/app/api/billing.py). So this page discovers billable
 * sessions from GET /billing/unbilled-orders — orders with no money settled
 * against them yet — rather than a raw unfiltered order list. A table's
 * session is reused across every visit it's ever had (see
 * billing_service.list_unbilled_orders for why), so grouping straight from
 * GET /orders would resurface a table's entire history on every visit;
 * this endpoint already excludes whatever a previous, settled bill covered.
 * Opening a session generates/fetches its real bill from the backend.
 */
export function BillingPage() {
  const { t } = useTranslation();
  const hotelRoomsEnabled = useIsFeatureEnabled("HOTEL_ROOMS");
  const { data: orders, isLoading, isError, isFetching, dataUpdatedAt, refetch } = useUnbilledOrders();
  const { data: tables } = useTables();
  const { data: rooms } = useRooms({ enabled: hotelRoomsEnabled });
  // A billable session's location can be a table OR a hotel room — both
  // are just Locations (see backend/app/models/location.py).
  const locations = useMemo(() => [...(tables ?? []), ...(rooms ?? [])], [tables, rooms]);
  const generateBill = useGenerateBill();
  const [openBillId, setOpenBillId] = useState<string | null>(null);
  const [activeSource, setActiveSource] = useState<OrderOut["source"] | undefined>(undefined);
  const [generatingSession, setGeneratingSession] = useState<string | null>(null);

  const sessions = useMemo(() => {
    if (!orders) return [];
    const map = new Map<string, { sessionId: string; locationId: string | null; orders: OrderOut[] }>();
    for (const order of orders) {
      if (order.status === "CANCELLED") continue;
      const entry = map.get(order.session_id);
      if (entry) entry.orders.push(order);
      else map.set(order.session_id, { sessionId: order.session_id, locationId: order.location_id, orders: [order] });
    }
    return [...map.values()];
  }, [orders]);

  const tableName = (locationId: string | null) => locations.find((loc) => loc.id === locationId)?.name ?? "—";

  const handleOpenSession = (sessionId: string, source: OrderOut["source"]) => {
    setGeneratingSession(sessionId);
    generateBill.mutate(
      { session_id: sessionId },
      {
        onSuccess: (bill) => {
          setActiveSource(source);
          setOpenBillId(bill.id);
        },
        onError: (err) => toast.error(parseApiError(err).message),
        onSettled: () => setGeneratingSession(null),
      }
    );
  };

  return (
    <div>
      <PageHeader
        title={t("nav.billing")}
        subtitle={t("billing.subtitle")}
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
          <p className="text-sm font-medium">{t("orders.loadError")}</p>
        </div>
      )}

      {!isLoading && !isError && sessions.length === 0 && (
        <p className="py-16 text-center text-sm text-stone-400">{t("billing.noSessions")}</p>
      )}

      {!isLoading && !isError && sessions.length > 0 && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {sessions.map((session) => (
            <Card key={session.sessionId} className="p-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-bold text-stone-900">{tableName(session.locationId)}</p>
                  <p className="text-xs text-stone-500">{t(`orderSource.${session.orders[0].source}`)}</p>
                </div>
                <Receipt size={18} className="text-stone-300" />
              </div>

              <p className="mt-2 text-xs text-stone-500">{t("billing.ordersInSession", { count: session.orders.length })}</p>
              <ul className="mt-1 space-y-0.5">
                {session.orders.map((o) => (
                  <li key={o.id} className="truncate text-xs text-stone-400">
                    {o.order_number}
                  </li>
                ))}
              </ul>

              <button
                type="button"
                onClick={() => handleOpenSession(session.sessionId, session.orders[0].source)}
                disabled={generatingSession === session.sessionId}
                className="mt-3 w-full rounded-lg bg-brand-600 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
              >
                {generatingSession === session.sessionId ? t("common.loading") : t("billing.viewBill")}
              </button>
            </Card>
          ))}
        </div>
      )}

      <BillDetailDialog
        billId={openBillId}
        tables={locations}
        source={activeSource}
        onClose={() => setOpenBillId(null)}
      />
    </div>
  );
}
