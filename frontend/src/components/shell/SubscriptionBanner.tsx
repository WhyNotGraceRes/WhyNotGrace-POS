import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { AlertTriangle } from "lucide-react";

import { useSubscription } from "@/features/subscription/hooks";

/** Persistent warning strip shown across the dashboard once a business's
 * plan lapses — GRACE (still working, 3-day warning) or SUSPENDED (see
 * app.main.SubscriptionGateMiddleware, which is what's actually blocking
 * requests by the time this shows SUSPENDED; this banner is the
 * explanation, not the enforcement). Not shown for ACTIVE/NOT_CONFIGURED/
 * CANCELLED — a business that never had a plan or deliberately ended one
 * isn't "behind" in the way this banner means.
 */
export function SubscriptionBanner() {
  const { t } = useTranslation();
  const { data: subscription } = useSubscription();

  if (subscription?.status !== "GRACE" && subscription?.status !== "SUSPENDED") {
    return null;
  }

  const isSuspended = subscription.status === "SUSPENDED";

  return (
    <Link
      to="/subscription"
      className={
        "flex items-center justify-center gap-2 px-4 py-2 text-center text-sm font-medium text-white " +
        (isSuspended ? "bg-danger-600 hover:bg-danger-700" : "bg-warning-600 hover:bg-warning-700")
      }
    >
      <AlertTriangle size={15} />
      {isSuspended ? t("subscription.banner.suspended") : t("subscription.banner.grace")}
    </Link>
  );
}
