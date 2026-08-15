import { useTranslation } from "react-i18next";
import {
  IndianRupee,
  ShoppingBag,
  Clock,
  ChefHat,
  CheckCircle2,
  UtensilsCrossed,
  BedDouble,
  Receipt,
  CreditCard,
  Users,
  Gift,
  Package,
  Truck,
  Globe,
  AlertTriangle,
  RotateCcw,
} from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { formatCurrency, formatNumber } from "@/lib/format";
import { useDashboard } from "@/features/dashboard/hooks";
import { useFeatureFlags } from "@/features/settings/hooks";
import { StatCard, StatCardSkeleton } from "@/features/dashboard/components/StatCard";

export function DashboardPage() {
  const { t } = useTranslation();
  const { data, isLoading, isError, refetch, isFetching } = useDashboard();
  const { data: flags } = useFeatureFlags();

  const isEnabled = (module: string) => flags?.find((f) => f.module === module)?.enabled ?? false;

  return (
    <div>
      <PageHeader title={t("dashboard.title")} subtitle={t("dashboard.subtitle")} />

      {isError && (
        <Card className="mb-6 flex items-center justify-between gap-4 border-danger-200 bg-danger-50 p-4">
          <div className="flex items-center gap-3">
            <AlertTriangle size={20} className="shrink-0 text-danger-600" />
            <div>
              <p className="text-sm font-semibold text-danger-700">{t("dashboard.loadError")}</p>
              <p className="text-sm text-danger-600">{t("dashboard.loadErrorSubtitle")}</p>
            </div>
          </div>
          <Button variant="danger" size="sm" onClick={() => void refetch()} isLoading={isFetching}>
            <RotateCcw size={14} />
            {t("dashboard.retry")}
          </Button>
        </Card>
      )}

      {isLoading && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            <StatCard label={t("dashboard.salesToday")} value={formatCurrency(data.sales_today)} icon={IndianRupee} />
            <StatCard label={t("dashboard.ordersToday")} value={formatNumber(data.orders_today)} icon={ShoppingBag} />
            <StatCard
              label={t("dashboard.pendingOrders")}
              value={formatNumber(data.pending_orders)}
              icon={Clock}
              tone={data.pending_orders > 0 ? "warning" : "default"}
            />
            <StatCard
              label={t("dashboard.kotQueue")}
              value={formatNumber(data.kot_queue)}
              icon={ChefHat}
              tone={data.kot_queue > 0 ? "warning" : "default"}
            />
            <StatCard
              label={t("dashboard.readyOrders")}
              value={formatNumber(data.ready_orders)}
              icon={CheckCircle2}
              tone={data.ready_orders > 0 ? "success" : "default"}
            />
            {data.tables_total > 0 && (
              <StatCard
                label={t("dashboard.tables")}
                value={`${data.tables_occupied}/${data.tables_total}`}
                icon={UtensilsCrossed}
              />
            )}
            {data.rooms_total > 0 && (
              <StatCard
                label={t("dashboard.rooms")}
                value={`${data.rooms_occupied}/${data.rooms_total}`}
                icon={BedDouble}
              />
            )}
            <StatCard
              label={t("dashboard.pendingBills")}
              value={formatNumber(data.pending_bills)}
              icon={Receipt}
              tone={data.pending_bills > 0 ? "warning" : "default"}
            />
            <StatCard
              label={t("dashboard.paymentsToday")}
              value={formatNumber(data.payments_today_count)}
              hint={formatCurrency(data.payments_today_amount)}
              icon={CreditCard}
            />
            {data.orders_today > 0 && (
              <StatCard
                label={t("dashboard.avgOrderValue")}
                value={formatCurrency(data.sales_today / data.orders_today)}
                icon={IndianRupee}
              />
            )}
            <StatCard label={t("dashboard.customers")} value={formatNumber(data.customer_count)} icon={Users} />

            {isEnabled("LOYALTY") && (
              <StatCard
                label={t("dashboard.loyaltyAccounts")}
                value={formatNumber(data.loyalty_accounts)}
                hint={`${formatNumber(data.loyalty_points_outstanding)} ${t("dashboard.loyaltyPoints").toLowerCase()}`}
                icon={Gift}
              />
            )}
            {isEnabled("PICKUP") && (
              <StatCard label={t("dashboard.pickupToday")} value={formatNumber(data.pickup_orders_today)} icon={Package} />
            )}
            {isEnabled("DELIVERY") && (
              <StatCard label={t("dashboard.deliveryToday")} value={formatNumber(data.delivery_orders_today)} icon={Truck} />
            )}
            {isEnabled("ONLINE_WEBSITE") && (
              <StatCard label={t("dashboard.websiteToday")} value={formatNumber(data.website_orders_today)} icon={Globe} />
            )}
          </div>

          <Card className="mt-6 p-5">
            <h2 className="text-sm font-bold text-slate-900">{t("dashboard.popularItems")}</h2>
            <p className="text-xs text-slate-500">{t("dashboard.popularItemsSubtitle")}</p>

            {data.top_menu_items.length === 0 ? (
              <p className="mt-4 text-sm text-slate-400">{t("dashboard.noPopularItems")}</p>
            ) : (
              <ul className="mt-4 divide-y divide-slate-100">
                {data.top_menu_items.map((item, index) => (
                  <li key={item.menu_item_id} className="flex items-center justify-between gap-3 py-2.5">
                    <div className="flex items-center gap-3">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-500">
                        {index + 1}
                      </span>
                      <span className="text-sm font-medium text-slate-800">{item.name}</span>
                    </div>
                    <span className="text-sm font-semibold tabular-nums text-slate-600">
                      {formatNumber(item.quantity_sold)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
