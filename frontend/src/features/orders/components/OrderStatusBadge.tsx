import { useTranslation } from "react-i18next";
import { cn } from "@/lib/cn";
import type { OrderStatus } from "@/types/models";

const STATUS_CLASSES: Record<OrderStatus, string> = {
  PLACED: "bg-stone-100 text-stone-600",
  CONFIRMED: "bg-brand-50 text-brand-700",
  PREPARING: "bg-warning-50 text-warning-600",
  READY: "bg-success-50 text-success-600",
  OUT_FOR_DELIVERY: "bg-brand-50 text-brand-700",
  SERVED: "bg-success-50 text-success-700",
  DELIVERED: "bg-success-50 text-success-700",
  COMPLETED: "bg-success-50 text-success-700",
  CANCELLED: "bg-danger-50 text-danger-600",
};

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  const { t } = useTranslation();
  return (
    <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-semibold", STATUS_CLASSES[status])}>
      {t(`orderStatus.${status}`)}
    </span>
  );
}
