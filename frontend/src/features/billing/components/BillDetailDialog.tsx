import { useTranslation } from "react-i18next";
import { AlertTriangle } from "lucide-react";

import { Dialog } from "@/components/ui/Dialog";
import { Spinner } from "@/components/ui/Spinner";
import { formatCurrency } from "@/lib/format";
import { useAuthStore } from "@/stores/authStore";
import { useBusiness } from "@/features/business/hooks";
import { useBill } from "@/features/billing/hooks";
import { BillItemsList } from "@/features/billing/components/BillItemsList";
import { BillStatusBadge } from "@/features/billing/components/BillStatusBadge";
import { DiscountForm } from "@/features/billing/components/DiscountForm";
import { PaymentPanel } from "@/features/billing/components/PaymentPanel";
import { ReceiptView } from "@/features/billing/components/ReceiptView";
import { PrintBillButtons } from "@/features/billing/components/PrintBillButtons";
import type { LocationOut, OrderSource } from "@/types/models";

const DISCOUNT_ROLES = new Set(["OWNER", "MANAGER"]);

export function BillDetailDialog({
  billId,
  tables,
  source,
  onClose,
}: {
  billId: string | null;
  tables: LocationOut[];
  source?: OrderSource;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const role = useAuthStore((s) => s.user?.role);
  const { data: business } = useBusiness();
  const { data: bill, isLoading, isError } = useBill(billId);

  const canApplyDiscount = role && DISCOUNT_ROLES.has(role);
  const table = bill ? tables.find((tb) => tb.id === bill.location_id) : undefined;
  const remaining = bill ? Math.max(0, Math.round((bill.grand_total - bill.amount_paid) * 100) / 100) : 0;

  return (
    <Dialog open={Boolean(billId)} onClose={onClose} title={bill?.bill_number ?? t("billing.title")} size="lg">
      {isLoading && (
        <div className="flex justify-center py-10">
          <Spinner className="text-brand-600" />
        </div>
      )}

      {isError && (
        <div className="flex flex-col items-center gap-2 py-10 text-danger-600">
          <AlertTriangle size={22} />
          <p className="text-sm font-medium">{t("billing.loadError")}</p>
        </div>
      )}

      {bill && (
        <div className="space-y-5">
          <div className="flex items-center gap-2">
            <BillStatusBadge status={bill.status} />
            {table && <span className="text-sm text-slate-500">{table.name}</span>}
          </div>

          <BillItemsList bill={bill} />

          <div className="space-y-1 rounded-lg bg-slate-50 p-3 text-sm">
            <Row label={t("orders.subtotal")} value={formatCurrency(bill.subtotal)} />
            {bill.discounts.map((d) => (
              <Row key={d.id} label={`${t("billing.discount")}: ${d.name}`} value={`-${formatCurrency(d.amount)}`} tone="success" />
            ))}
            {bill.taxes.map((tax) => (
              <Row key={tax.id} label={`${tax.name}${tax.percent != null ? ` (${tax.percent}%)` : ""}`} value={formatCurrency(tax.amount)} />
            ))}
            {bill.service_charges.map((sc) => (
              <Row key={sc.id} label={`${sc.name}${sc.percent != null ? ` (${sc.percent}%)` : ""}`} value={formatCurrency(sc.amount)} />
            ))}
            <div className="my-1 border-t border-slate-200" />
            <Row label={t("billing.grandTotal")} value={formatCurrency(bill.grand_total)} bold />
            <Row label={t("billing.amountPaid")} value={formatCurrency(bill.amount_paid)} />
            {remaining > 0 && <Row label={t("billing.remaining")} value={formatCurrency(remaining)} tone="danger" bold />}
          </div>

          {canApplyDiscount && <DiscountForm bill={bill} />}

          {bill.status !== "PAID" && bill.status !== "CANCELLED" && (
            <div className="border-t border-slate-100 pt-4">
              <PaymentPanel bill={bill} />
            </div>
          )}

          {/* Printing is offered for any bill that exists, not only paid
              ones — a counter routinely hands a guest the bill before they
              pay. The server marks an unsettled copy as such. */}
          <div className="border-t border-slate-100 pt-4">
            <PrintBillButtons bill={bill} />
          </div>

          {bill.status === "PAID" && business && (
            <div className="border-t border-slate-100 pt-4">
              <ReceiptView bill={bill} businessName={business.name} tableName={table?.name} source={source} />
            </div>
          )}
        </div>
      )}
    </Dialog>
  );
}

function Row({
  label,
  value,
  bold,
  tone,
}: {
  label: string;
  value: string;
  bold?: boolean;
  tone?: "success" | "danger";
}) {
  return (
    <div
      className={
        "flex items-center justify-between " +
        (bold ? "text-base font-bold text-slate-900" : "text-slate-600") +
        (tone === "success" ? " text-success-700" : tone === "danger" ? " text-danger-600" : "")
      }
    >
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}
