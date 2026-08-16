import { useTranslation } from "react-i18next";
import { cn } from "@/lib/cn";
import type { SubscriptionOut } from "@/types/models";

const STATUS_CLASSES: Record<SubscriptionOut["status"], string> = {
  NOT_CONFIGURED: "bg-slate-100 text-slate-600",
  PENDING: "bg-warning-50 text-warning-600",
  ACTIVE: "bg-success-50 text-success-700",
  GRACE: "bg-warning-50 text-warning-700",
  SUSPENDED: "bg-danger-50 text-danger-600",
  PAYMENT_FAILED: "bg-danger-50 text-danger-600",
  CANCELLED: "bg-slate-100 text-slate-600",
  EXPIRED: "bg-danger-50 text-danger-600",
};

export function SubscriptionStatusBadge({ status }: { status: SubscriptionOut["status"] }) {
  const { t } = useTranslation();
  return (
    <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-semibold", STATUS_CLASSES[status])}>
      {t(`subscription.status.${status}`)}
    </span>
  );
}
