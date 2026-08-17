import { useTranslation } from "react-i18next";
import { AlertTriangle, CreditCard } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { formatCurrency } from "@/lib/format";
import { useSubscription } from "@/features/subscription/hooks";
import { SubscriptionStatusBadge } from "@/features/subscription/components/SubscriptionStatusBadge";

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
}

/** Read-only — see backend/app/api/subscription.py. Plans are set by
 * WhyNotGrace staff, not self-checkout; this page shows what was agreed
 * and its current status, nothing more. */
export function SubscriptionPage() {
  const { t } = useTranslation();
  const { data: subscription, isLoading, isError } = useSubscription();

  return (
    <div>
      <PageHeader title={t("nav.subscription")} subtitle={t("subscription.subtitle")} />

      {isLoading && (
        <div className="flex justify-center py-16">
          <Spinner className="text-brand-600" />
        </div>
      )}

      {isError && (
        <div className="flex flex-col items-center gap-2 py-16 text-danger-600">
          <AlertTriangle size={22} />
          <p className="text-sm font-medium">{t("subscription.loadError")}</p>
        </div>
      )}

      {!isLoading && !isError && subscription && (
        <Card className="max-w-xl p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                <CreditCard size={20} />
              </div>
              <div>
                <p className="text-sm font-semibold text-stone-500">
                  {subscription.plan_name ?? t("subscription.noPlan")}
                </p>
                {subscription.amount != null && (
                  <p className="text-lg font-bold text-stone-900">
                    {formatCurrency(subscription.amount)}
                    <span className="text-sm font-normal text-stone-500">/{t("subscription.month")}</span>
                  </p>
                )}
              </div>
            </div>
            <SubscriptionStatusBadge status={subscription.status} />
          </div>

          <div className="mt-4 space-y-2 border-t border-stone-100 pt-4 text-sm">
            {subscription.current_period_start && (
              <div className="flex justify-between">
                <span className="text-stone-500">{t("subscription.startedOn")}</span>
                <span className="font-medium text-stone-800">{formatDate(subscription.current_period_start)}</span>
              </div>
            )}
            {(subscription.status === "ACTIVE" || subscription.status === "GRACE") && subscription.current_period_end && (
              <div className="flex justify-between">
                <span className="text-stone-500">{t("subscription.nextBillingDate")}</span>
                <span className="font-medium text-stone-800">{formatDate(subscription.current_period_end)}</span>
              </div>
            )}
            {subscription.status === "SUSPENDED" && (
              <p className="text-danger-600">{t("subscription.suspendedNotice")}</p>
            )}
            {subscription.status === "GRACE" && <p className="text-warning-700">{t("subscription.graceNotice")}</p>}
            {subscription.status === "CANCELLED" && subscription.cancelled_at && (
              <div className="flex justify-between">
                <span className="text-stone-500">{t("subscription.cancelledOn")}</span>
                <span className="font-medium text-stone-800">{formatDate(subscription.cancelled_at)}</span>
              </div>
            )}
            {subscription.status === "NOT_CONFIGURED" && (
              <p className="text-stone-500">{t("subscription.notConfiguredNotice")}</p>
            )}
          </div>

          <p className="mt-5 rounded-lg border border-stone-200 bg-stone-50 px-3 py-2.5 text-xs text-stone-600">
            {t("subscription.contactToChange")}
          </p>
        </Card>
      )}
    </div>
  );
}
