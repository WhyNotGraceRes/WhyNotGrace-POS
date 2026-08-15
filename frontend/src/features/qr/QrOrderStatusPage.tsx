import { useTranslation } from "react-i18next";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { AlertTriangle, Check, ChefHat, ClipboardList, PartyPopper } from "lucide-react";

import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import { formatCurrency } from "@/lib/format";
import { cn } from "@/lib/cn";
import { useQrSessionBootstrap } from "@/features/qr/useQrSession";
import { useQrOrderStatus } from "@/features/qr/hooks";
import { useQrSessionStore } from "@/stores/qrSessionStore";
import type { OrderStatus } from "@/types/models";

const PROGRESS_STEPS: { status: OrderStatus; icon: typeof ClipboardList }[] = [
  { status: "PLACED", icon: ClipboardList },
  { status: "CONFIRMED", icon: Check },
  { status: "PREPARING", icon: ChefHat },
  { status: "READY", icon: PartyPopper },
  { status: "SERVED", icon: Check },
];

function stepIndex(status: OrderStatus): number {
  const idx = PROGRESS_STEPS.findIndex((s) => s.status === status);
  if (idx >= 0) return idx;
  // DELIVERED / COMPLETED land past the last dine-in step.
  if (status === "DELIVERED" || status === "COMPLETED") return PROGRESS_STEPS.length - 1;
  return 0;
}

export function QrOrderStatusPage() {
  const { t } = useTranslation();
  const { businessSlug = "", kind = "table", locationId = "", orderId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const code = searchParams.get("c");

  const { status, errorMessage } = useQrSessionBootstrap(businessSlug, locationId, code);
  const sessionToken = useQrSessionStore((s) => s.sessionToken);

  const { data: order, isError } = useQrOrderStatus(sessionToken, orderId);

  const menuUrl = `/qr/menu/${businessSlug}/${kind}/${locationId}`;

  if (status === "loading") {
    return (
      <div className="flex min-h-[70vh] flex-col items-center justify-center gap-3 px-6 text-center">
        <Spinner size={26} className="text-brand-600" />
        <p className="text-sm text-slate-500">{t("qr.loadingSession")}</p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="flex min-h-[70vh] flex-col items-center justify-center gap-3 px-6 text-center">
        <AlertTriangle size={28} className="text-danger-500" />
        <p className="text-base font-semibold text-slate-800">{t("qr.invalidLink")}</p>
        <p className="text-sm text-slate-500">{errorMessage || t("qr.invalidLinkHint")}</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex min-h-[70vh] flex-col items-center justify-center gap-3 px-6 text-center">
        <AlertTriangle size={28} className="text-danger-500" />
        <p className="text-sm font-medium text-slate-700">{t("qr.status.loadError")}</p>
      </div>
    );
  }

  // No error, but no data yet either — this covers the genuine first
  // fetch AND the transient render where the query has just gone from
  // disabled to enabled but hasn't reached fetchStatus "fetching" yet
  // (isLoading is briefly false there too). Once `order` has ever been
  // populated, background refetches (polling) keep showing it — no
  // spinner flash on every poll tick.
  if (!order) {
    return (
      <div className="flex min-h-[70vh] items-center justify-center">
        <Spinner size={26} className="text-brand-600" />
      </div>
    );
  }

  const currentStep = stepIndex(order.status);
  const isCancelled = order.status === "CANCELLED";

  return (
    <div className="px-4 py-6 pb-10">
      <div className="flex flex-col items-center gap-2 text-center">
        {!isCancelled && (
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-success-50 text-success-600">
            <Check size={24} />
          </span>
        )}
        <h1 className="text-lg font-bold text-slate-900">
          {isCancelled ? t("qr.status.cancelledTitle") : t("qr.status.confirmedTitle")}
        </h1>
        <p className="text-sm text-slate-500">{t("qr.status.orderNumber", { number: order.order_number })}</p>
      </div>

      {!isCancelled && (
        <div className="mt-6 flex items-center justify-between px-2">
          {PROGRESS_STEPS.map((step, idx) => {
            const Icon = step.icon;
            const reached = idx <= currentStep;
            return (
              <div key={step.status} className="flex flex-1 flex-col items-center gap-1.5">
                <div className="flex w-full items-center">
                  {idx > 0 && (
                    <span className={cn("h-0.5 flex-1", idx <= currentStep ? "bg-brand-500" : "bg-slate-200")} />
                  )}
                  <span
                    className={cn(
                      "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
                      reached ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-400"
                    )}
                  >
                    <Icon size={15} />
                  </span>
                  {idx < PROGRESS_STEPS.length - 1 && (
                    <span className={cn("h-0.5 flex-1", idx < currentStep ? "bg-brand-500" : "bg-slate-200")} />
                  )}
                </div>
                <span className={cn("text-center text-[10px] font-semibold", reached ? "text-brand-700" : "text-slate-400")}>
                  {t(`qr.status.steps.${step.status}`)}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {isCancelled && (
        <p className="mt-4 rounded-lg border border-danger-500/30 bg-danger-50 px-4 py-3 text-center text-sm text-danger-700">
          {t("qr.status.cancelledBody")}
        </p>
      )}

      <div className="mt-6 rounded-card border border-slate-100 p-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">{t("qr.status.items")}</p>
        <ul className="space-y-2">
          {order.items.map((item) => (
            <li key={item.id} className="flex items-start justify-between gap-2 text-sm">
              <div>
                <p className="font-medium text-slate-800">
                  {item.quantity} × {item.item_name_snapshot}
                </p>
                {item.options.length > 0 && (
                  <p className="text-xs text-slate-500">{item.options.map((o) => o.option_name_snapshot).join(", ")}</p>
                )}
              </div>
              <span className="shrink-0 font-semibold text-slate-700">{formatCurrency(item.line_total)}</span>
            </li>
          ))}
        </ul>
        <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3 text-sm font-bold text-slate-900">
          <span>{t("orders.subtotal")}</span>
          <span>{formatCurrency(order.subtotal)}</span>
        </div>
      </div>

      <Link to={menuUrl} className="mt-6 block">
        <Button variant="secondary" className="w-full">
          {t("qr.status.orderMore")}
        </Button>
      </Link>
    </div>
  );
}
