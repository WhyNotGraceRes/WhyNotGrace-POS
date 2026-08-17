import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Wallet, ChevronRight } from "lucide-react";

import { Card } from "@/components/ui/Card";
import { cn } from "@/lib/cn";
import { elapsedSince, formatCurrency } from "@/lib/format";
import { useShiftReport } from "@/features/shifts/hooks";
import type { ShiftOut } from "@/types/models";

/** The first thing a cashier needs to know: is the drawer even open. No
 * shift open reads as "needs action" (warning) since nothing can be billed
 * until one is — an open shift is quiet/success, matching the tone
 * language used across the dashboard. Always links to /shift, whether
 * that's to open one or to check on the one already running. */
export function ShiftStatusCard({ shift }: { shift: ShiftOut | null }) {
  const { t } = useTranslation();

  const isOpen = shift !== null;
  // gross_takings (every payment method, not just cash) is always visible,
  // open shift or not — only expected_cash is withheld while blind cash
  // counting is on, since that's the specific number a cashier could copy
  // instead of counting the drawer. Showing takings-so-far here doesn't
  // touch that control.
  const { data: report } = useShiftReport(shift?.id ?? null);
  const elapsed = isOpen ? elapsedSince(new Date(shift.opened_at).getTime()) : null;
  const openedLabel = elapsed
    ? elapsed.unit === "now"
      ? t("roleHome.shiftOpenedJustNow")
      : elapsed.unit === "seconds"
        ? t("roleHome.shiftOpenedSecondsAgo", { count: elapsed.count })
        : elapsed.unit === "minutes"
          ? t("roleHome.shiftOpenedMinutesAgo", { count: elapsed.count })
          : t("roleHome.shiftOpenedHoursAgo", { count: elapsed.count })
    : null;

  const toneClasses = isOpen
    ? { icon: "bg-success-50 text-success-600", ring: "ring-1 ring-success-200" }
    : { icon: "bg-warning-50 text-warning-600", ring: "ring-1 ring-warning-200" };

  return (
    <Link to="/shift" className="block">
      <Card className={cn("flex items-center gap-3 p-4 transition-shadow hover:shadow-md", toneClasses.ring)}>
        <div className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-lg", toneClasses.icon)}>
          <Wallet size={19} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-slate-500">
            {isOpen ? t("roleHome.shiftOpen") : t("roleHome.shiftClosed")}
          </p>
          <p className="mt-0.5 truncate text-sm font-bold text-slate-900">
            {isOpen ? openedLabel : t("roleHome.openShiftCta")}
          </p>
          {isOpen && (
            <p className="mt-0.5 truncate text-xs text-slate-400">
              {t("roleHome.shiftOpeningFloat", { amount: formatCurrency(shift.opening_float) })}
              {report && ` · ${t("roleHome.shiftCollected", { amount: formatCurrency(report.gross_takings) })}`}
            </p>
          )}
        </div>
        <ChevronRight size={16} className="shrink-0 text-slate-300" />
      </Card>
    </Link>
  );
}

export function ShiftStatusCardSkeleton() {
  return (
    <Card className="flex items-center gap-3 p-4">
      <div className="h-10 w-10 shrink-0 animate-pulse rounded-lg bg-slate-200" />
      <div className="min-w-0 flex-1 space-y-2">
        <div className="h-3 w-16 animate-pulse rounded bg-slate-200" />
        <div className="h-4 w-24 animate-pulse rounded bg-slate-200" />
      </div>
    </Card>
  );
}
