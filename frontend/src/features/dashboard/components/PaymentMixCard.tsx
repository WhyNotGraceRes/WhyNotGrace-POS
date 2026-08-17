import { useTranslation } from "react-i18next";
import { Banknote, Smartphone, CreditCard, Wifi, HelpCircle } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { formatCurrency } from "@/lib/format";
import type { PaymentMethodBreakdownOut } from "@/types/models";

const METHOD_ICON: Record<string, typeof Banknote> = {
  CASH: Banknote,
  UPI: Smartphone,
  CARD: CreditCard,
  ONLINE: Wifi,
  OTHER: HelpCircle,
};

const METHOD_LABEL_KEY: Record<string, string> = {
  CASH: "dashboard.methodCash",
  UPI: "dashboard.methodUpi",
  CARD: "dashboard.methodCard",
  ONLINE: "dashboard.methodOnline",
  OTHER: "dashboard.methodOther",
};

/** What a cashier or owner actually checks at day-end — cash vs. card vs.
 * UPI vs. online, reconciled against what's in the drawer. Petpooja shows
 * this as a set of separate mini-widgets scattered around the page; here
 * it's one grouped comparison, same visual language as ChannelBreakdown,
 * so the two "where did today's money/orders come from" questions read
 * the same way. */
export function PaymentMixCard({ breakdown }: { breakdown: PaymentMethodBreakdownOut[] }) {
  const { t } = useTranslation();

  const rows = breakdown.filter((r) => r.count > 0);
  if (rows.length === 0) return null;

  const total = rows.reduce((sum, r) => sum + r.total_amount, 0);
  const max = Math.max(1, ...rows.map((r) => r.total_amount));

  return (
    <Card className="p-5">
      <h2 className="text-sm font-bold text-slate-900">{t("dashboard.paymentMix")}</h2>
      <p className="text-xs text-slate-500">{t("dashboard.paymentMixSubtitle")}</p>

      <ul className="mt-4 space-y-3">
        {rows.map((row) => {
          const Icon = METHOD_ICON[row.method] ?? HelpCircle;
          const labelKey = METHOD_LABEL_KEY[row.method];
          return (
            <li key={row.method} className="flex items-center gap-3">
              <Icon size={16} className="shrink-0 text-slate-400" />
              <span className="w-16 shrink-0 text-xs font-medium text-slate-600">
                {labelKey ? t(labelKey) : row.method}
              </span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-brand-500"
                  style={{ width: `${(row.total_amount / max) * 100}%` }}
                />
              </div>
              <span className="w-20 shrink-0 text-right text-sm font-semibold tabular-nums text-slate-800">
                {formatCurrency(row.total_amount)}
              </span>
            </li>
          );
        })}
      </ul>

      <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-xs">
        <span className="font-medium text-slate-500">{t("dashboard.paymentMixTotal")}</span>
        <span className="font-bold tabular-nums text-slate-800">{formatCurrency(total)}</span>
      </div>
    </Card>
  );
}
