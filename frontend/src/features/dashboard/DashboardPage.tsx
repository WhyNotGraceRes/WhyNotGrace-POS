import { useTranslation } from "react-i18next";
import {
  IndianRupee,
  ShoppingBag,
  TrendingUp,
  Clock,
  ChefHat,
  CheckCircle2,
  Receipt,
  UtensilsCrossed,
  BedDouble,
  CreditCard,
  Users,
  Gift,
  AlertTriangle,
  RotateCcw,
} from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { formatCurrency, formatNumber } from "@/lib/format";
import { useDashboard } from "@/features/dashboard/hooks";
import { useFeatureFlags } from "@/features/settings/hooks";
import { StatCard } from "@/features/dashboard/components/StatCard";
import { HeroStatCard, HeroStatCardSkeleton } from "@/features/dashboard/components/HeroStatCard";
import { ActionCard, ActionCardSkeleton } from "@/features/dashboard/components/ActionCard";
import { ChannelBreakdown } from "@/features/dashboard/components/ChannelBreakdown";

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
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <HeroStatCardSkeleton key={i} />
            ))}
          </div>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <ActionCardSkeleton key={i} />
            ))}
          </div>
        </div>
      )}

      {data && (
        <div className="space-y-6">
          {/* Tier 1 — headline totals. The 3-5 numbers an owner scans first;
              deliberately not clickable, these are totals to read, not
              queues to work through (see the action strip below). */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <HeroStatCard label={t("dashboard.salesToday")} value={formatCurrency(data.sales_today)} icon={IndianRupee} />
            <HeroStatCard label={t("dashboard.ordersToday")} value={formatNumber(data.orders_today)} icon={ShoppingBag} />
            <HeroStatCard
              label={t("dashboard.avgOrderValue")}
              value={data.orders_today > 0 ? formatCurrency(data.sales_today / data.orders_today) : formatCurrency(0)}
              icon={TrendingUp}
            />
          </div>

          {/* Tier 2 — needs attention right now. Every card is a queue with
              a real destination (Orders/Kitchen/Billing), not a dead end —
              the dashboard doubles as a launch pad into the work itself. */}
          <div>
            <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">
              {t("dashboard.needsAttention")}
            </h2>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <ActionCard label={t("dashboard.pendingOrders")} count={data.pending_orders} icon={Clock} to="/orders" />
              <ActionCard label={t("dashboard.kotQueue")} count={data.kot_queue} icon={ChefHat} to="/kitchen" />
              <ActionCard
                label={t("dashboard.readyOrders")}
                count={data.ready_orders}
                icon={CheckCircle2}
                to="/kitchen"
                positiveWhenNonZero
              />
              <ActionCard label={t("dashboard.pendingBills")} count={data.pending_bills} icon={Receipt} to="/billing" />
            </div>
          </div>

          {/* Tier 3 — grouped channel comparison and reference figures. */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ChannelBreakdown
              ordersToday={data.orders_today}
              pickupToday={data.pickup_orders_today}
              deliveryToday={data.delivery_orders_today}
              pickupEnabled={isEnabled("PICKUP")}
              deliveryEnabled={isEnabled("DELIVERY")}
            />

            <div className="grid grid-cols-2 gap-3">
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
                label={t("dashboard.paymentsToday")}
                value={formatNumber(data.payments_today_count)}
                hint={formatCurrency(data.payments_today_amount)}
                icon={CreditCard}
              />
              <StatCard label={t("dashboard.customers")} value={formatNumber(data.customer_count)} icon={Users} />
              {isEnabled("LOYALTY") && (
                <StatCard
                  label={t("dashboard.loyaltyAccounts")}
                  value={formatNumber(data.loyalty_accounts)}
                  hint={`${formatNumber(data.loyalty_points_outstanding)} ${t("dashboard.loyaltyPoints").toLowerCase()}`}
                  icon={Gift}
                />
              )}
            </div>
          </div>

          <Card className="p-5">
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
        </div>
      )}
    </div>
  );
}
