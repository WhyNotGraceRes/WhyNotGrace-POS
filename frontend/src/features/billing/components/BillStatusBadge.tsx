import { useTranslation } from "react-i18next";
import { cn } from "@/lib/cn";
import type { BillStatus } from "@/types/models";

const STATUS_CLASSES: Record<BillStatus, string> = {
  OPEN: "bg-stone-100 text-stone-600",
  PARTIALLY_PAID: "bg-warning-50 text-warning-600",
  PAID: "bg-success-50 text-success-700",
  CANCELLED: "bg-danger-50 text-danger-600",
};

export function BillStatusBadge({ status }: { status: BillStatus }) {
  const { t } = useTranslation();
  return (
    <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-semibold", STATUS_CLASSES[status])}>
      {t(`billStatus.${status}`)}
    </span>
  );
}
