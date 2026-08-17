import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Clock, UtensilsCrossed, Receipt, ChefHat, Truck } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { FreshnessIndicator } from "@/components/FreshnessIndicator";
import { Card } from "@/components/ui/Card";
import { cn } from "@/lib/cn";
import { minutesSince } from "@/lib/format";
import { useAuthStore } from "@/stores/authStore";
import { useBusiness } from "@/features/business/hooks";
import { useFeatureFlags } from "@/features/settings/hooks";
import { getVisibleNavItems } from "@/config/navigation";
import { useOrders } from "@/features/orders/hooks";
import { useTables } from "@/features/tables/hooks";
import { useCurrentShift } from "@/features/shifts/hooks";
import { useKitchenQueue } from "@/features/kitchen/hooks";
import { useDeliveryOrders } from "@/features/delivery/hooks";
import { ActionCard, ActionCardSkeleton } from "@/features/dashboard/components/ActionCard";
import { ShiftStatusCard, ShiftStatusCardSkeleton } from "@/features/home/components/ShiftStatusCard";
import type { FeatureModule } from "@/types/models";

/** Same >=80%-is-good-news read as the owner dashboard (see
 * DashboardPage.tsx's occupancyTone) — a full dining room isn't a problem
 * for whoever's seating people. */
function occupancyTone(occupied: number, total: number): "default" | "success" {
  return total > 0 && occupied / total >= 0.8 ? "success" : "default";
}

/**
 * Landing page for roles the backend does not grant dashboard access to
 * (CASH_COUNTER, SERVICE_COUNTER, KITCHEN, DELIVERY — see
 * backend/app/api/dashboard.py: GET /dashboard is OWNER/MANAGER only).
 * Rather than the empty quick-links stub this used to be, each role gets a
 * small live-data strip scoped to exactly what it's permitted to see and
 * can act on — same clickable-card language as the owner dashboard, but
 * every card here only links to a page this role can actually reach (see
 * config/navigation.ts). No "ready to serve" or "pending bills" widgets for
 * roles that have no screen to work them from — a card with nowhere real to
 * go is worse than no card.
 */
export function RoleHomePage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const { data: business } = useBusiness();
  const { data: flags } = useFeatureFlags();

  const role = user?.role;
  const isCashCounter = role === "CASH_COUNTER";
  const isServiceCounter = role === "SERVICE_COUNTER";
  const isKitchen = role === "KITCHEN";
  const isDelivery = role === "DELIVERY";

  const { data: shift, isLoading: shiftLoading } = useCurrentShift({ enabled: isCashCounter });
  const {
    data: pendingOrders,
    isLoading: ordersLoading,
    isFetching: ordersFetching,
    dataUpdatedAt: ordersUpdatedAt,
    refetch: refetchOrders,
  } = useOrders({ active_only: true }, { enabled: isCashCounter || isServiceCounter });
  const { data: tables, isLoading: tablesLoading } = useTables({ enabled: isCashCounter || isServiceCounter });
  const {
    data: kotQueue,
    isLoading: kotLoading,
    isFetching: kotFetching,
    dataUpdatedAt: kotUpdatedAt,
    refetch: refetchKot,
  } = useKitchenQueue({ enabled: isKitchen });
  const {
    data: deliveryOrders,
    isLoading: deliveryLoading,
    isFetching: deliveryFetching,
    dataUpdatedAt: deliveryUpdatedAt,
    refetch: refetchDelivery,
  } = useDeliveryOrders({ enabled: isDelivery });

  // Whichever query actually represents "how current is this screen" for
  // the signed-in role — the same freshness control the owner dashboard
  // shows, so a cashier or kitchen hand gets the same at-a-glance
  // confidence about the numbers in front of them.
  const freshness = isKitchen
    ? { dataUpdatedAt: kotUpdatedAt, isFetching: kotFetching, onRefresh: () => void refetchKot() }
    : isDelivery
      ? { dataUpdatedAt: deliveryUpdatedAt, isFetching: deliveryFetching, onRefresh: () => void refetchDelivery() }
      : isCashCounter || isServiceCounter
        ? { dataUpdatedAt: ordersUpdatedAt, isFetching: ordersFetching, onRefresh: () => void refetchOrders() }
        : null;

  const isFeatureEnabled = (module: FeatureModule) => flags?.find((f) => f.module === module)?.enabled ?? false;

  const items = user ? getVisibleNavItems(user.role, isFeatureEnabled).filter((i) => i.path !== "/") : [];

  if (!user) return null;

  const billsPendingCount = tables?.filter((table) => table.status === "BILL_PENDING").length ?? 0;
  const tablesOccupied = tables?.filter((table) => table.status !== "AVAILABLE").length ?? 0;
  const tablesTotal = tables?.length ?? 0;

  // A queue of 4 reads very differently depending on whether the oldest
  // ticket is 3 minutes old or 25 — the count alone can't tell a kitchen
  // that. Recomputed on every render off `created_at`, same as the KOT
  // cards' own age display, rather than trusting a cached "minutes ago".
  const oldestKotMinutes =
    kotQueue && kotQueue.length > 0 ? Math.max(...kotQueue.map((k) => minutesSince(k.created_at))) : null;

  // Same operational distinction as the kitchen queue's age: how many
  // deliveries are still being cooked vs. already out the door tells the
  // rider staff something the flat count can't.
  const outForDeliveryCount = deliveryOrders?.filter((o) => o.delivery_status === "OUT_FOR_DELIVERY").length ?? 0;
  const preparingDeliveryCount = (deliveryOrders?.length ?? 0) - outForDeliveryCount;

  const hasLiveStrip = isCashCounter || isServiceCounter || isKitchen || isDelivery;

  return (
    <div>
      <PageHeader
        title={t("roleHome.welcome", { name: user.first_name })}
        subtitle={t("roleHome.subtitle", { role: t(`roles.${user.role}`), business: business?.name ?? "…" })}
        actions={
          freshness ? (
            <FreshnessIndicator
              dataUpdatedAt={freshness.dataUpdatedAt}
              isFetching={freshness.isFetching}
              onRefresh={freshness.onRefresh}
            />
          ) : undefined
        }
      />

      {hasLiveStrip && (
        <div className="mt-6">
          <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-stone-400">
            {t("dashboard.needsAttention")}
          </h2>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {isCashCounter &&
              (shiftLoading ? <ShiftStatusCardSkeleton /> : <ShiftStatusCard shift={shift ?? null} />)}

            {(isCashCounter || isServiceCounter) &&
              (ordersLoading ? (
                <ActionCardSkeleton />
              ) : (
                <ActionCard
                  label={t("dashboard.pendingOrders")}
                  count={pendingOrders?.length ?? 0}
                  icon={Clock}
                  to="/orders"
                />
              ))}

            {isCashCounter &&
              (tablesLoading ? (
                <ActionCardSkeleton />
              ) : (
                <ActionCard
                  label={t("dashboard.pendingBills")}
                  count={billsPendingCount}
                  icon={Receipt}
                  to="/billing"
                />
              ))}

            {isServiceCounter &&
              (tablesLoading ? (
                <ActionCardSkeleton />
              ) : (
                <Link to="/tables" className="block">
                  <Card
                    className={cn(
                      "interactive-card flex items-center gap-3 p-4",
                      occupancyTone(tablesOccupied, tablesTotal) === "success" && "ring-1 ring-success-200"
                    )}
                  >
                    <div
                      className={cn(
                        "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl",
                        occupancyTone(tablesOccupied, tablesTotal) === "success"
                          ? "bg-success-50 text-success-600"
                          : "bg-brand-50 text-brand-700"
                      )}
                    >
                      <UtensilsCrossed size={19} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-medium text-stone-500">{t("dashboard.tables")}</p>
                      <p className="mt-0.5 text-2xl font-bold tracking-tight tabular-nums text-stone-900">
                        {tablesOccupied}/{tablesTotal}
                      </p>
                    </div>
                  </Card>
                </Link>
              ))}

            {isKitchen &&
              (kotLoading ? (
                <ActionCardSkeleton />
              ) : (
                <ActionCard
                  label={t("dashboard.kotQueue")}
                  count={kotQueue?.length ?? 0}
                  icon={ChefHat}
                  to="/kitchen"
                  hint={oldestKotMinutes !== null ? t("roleHome.oldestTicket", { minutes: oldestKotMinutes }) : undefined}
                />
              ))}

            {isDelivery &&
              (deliveryLoading ? (
                <ActionCardSkeleton />
              ) : (
                <ActionCard
                  label={t("roleHome.activeDeliveries")}
                  count={deliveryOrders?.length ?? 0}
                  icon={Truck}
                  to="/delivery"
                  hint={
                    deliveryOrders && deliveryOrders.length > 0
                      ? t("roleHome.deliveryBreakdown", {
                          preparing: preparingDeliveryCount,
                          outForDelivery: outForDeliveryCount,
                        })
                      : undefined
                  }
                />
              ))}
          </div>
        </div>
      )}

      {items.length > 0 && (
        <div className="mt-6">
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-stone-400">
            {t("roleHome.quickLinks")}
          </h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {items.map((item) => (
              <Link key={item.path} to={item.path}>
                <Card className="interactive-card flex flex-col items-start gap-3 p-4">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
                    <item.icon size={18} />
                  </div>
                  <span className="text-sm font-semibold text-stone-800">{t(item.labelKey)}</span>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
