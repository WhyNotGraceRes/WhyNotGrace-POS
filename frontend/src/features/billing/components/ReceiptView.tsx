import { useTranslation } from "react-i18next";
import { Printer } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { formatCurrency } from "@/lib/format";
import type { BillOut, OrderSource } from "@/types/models";

/**
 * Printable receipt. Uses the browser's native print dialog (which
 * already offers "Save as PDF") rather than adding a PDF library — see
 * the `@media print` rule in src/index.css that hides everything on the
 * page except `.receipt-print-area`.
 *
 * Note: BillOut has no created_at/timestamp field, so this shows when the
 * receipt was rendered ("Printed on"), not a fabricated order time.
 */
export function ReceiptView({
  bill,
  businessName,
  tableName,
  source,
}: {
  bill: BillOut;
  businessName: string;
  tableName?: string;
  source?: OrderSource;
}) {
  const { t } = useTranslation();

  return (
    <div>
      <div className="receipt-print-area mx-auto max-w-sm rounded-lg border border-dashed border-slate-300 p-5 font-mono text-sm">
        <div className="text-center">
          <p className="text-base font-bold">{businessName}</p>
          <p className="mt-0.5 text-xs text-slate-500">{t("receipt.printedOn", { datetime: new Date().toLocaleString() })}</p>
          {bill.nc_at && (
            <p className="mt-1 text-xs font-bold">
              ** {t("billing.noChargeBanner")} **
              {bill.nc_reason ? <span className="block font-normal">{bill.nc_reason}</span> : null}
            </p>
          )}
        </div>

        <div className="my-3 border-t border-dashed border-slate-300" />

        <div className="space-y-0.5 text-xs">
          <div className="flex justify-between">
            <span>{t("orders.orderNumber")}</span>
            <span className="font-semibold">{bill.bill_number}</span>
          </div>
          {tableName && (
            <div className="flex justify-between">
              <span>{t("orders.table")}</span>
              <span>{tableName}</span>
            </div>
          )}
          {source && (
            <div className="flex justify-between">
              <span>{t("orders.source")}</span>
              <span>{t(`orderSource.${source}`)}</span>
            </div>
          )}
        </div>

        <div className="my-3 border-t border-dashed border-slate-300" />

        {/* This is the guest's copy on screen, so it follows the same rules as
            the printed one (see services/receipt/builder.py): a voided line
            never appears, and a complimentary line does appear — marked NC,
            because the point of comping is that the guest sees it. */}
        <ul className="space-y-1">
          {bill.items
            .filter((item) => !item.voided_at)
            .map((item) => (
              <li key={item.id} className="flex justify-between text-xs">
                <span className="pr-2">
                  {item.quantity} × {item.item_name_snapshot}
                </span>
                <span className="shrink-0">
                  {item.comped_at ? t("billing.nc") : formatCurrency(item.line_total)}
                </span>
              </li>
            ))}
        </ul>

        <div className="my-3 border-t border-dashed border-slate-300" />

        <div className="space-y-0.5 text-xs">
          <div className="flex justify-between">
            <span>{t("orders.subtotal")}</span>
            <span>{formatCurrency(bill.subtotal)}</span>
          </div>
          {bill.discounts.map((d) => (
            <div key={d.id} className="flex justify-between text-success-700">
              <span>
                {t("billing.discount")}: {d.name}
              </span>
              <span>-{formatCurrency(d.amount)}</span>
            </div>
          ))}
          {bill.taxes.map((tax) => (
            <div key={tax.id} className="flex justify-between">
              <span>
                {tax.name} {tax.percent != null ? `(${tax.percent}%)` : ""}
              </span>
              <span>{formatCurrency(tax.amount)}</span>
            </div>
          ))}
          {bill.service_charges.map((sc) => (
            <div key={sc.id} className="flex justify-between">
              <span>
                {sc.name} {sc.percent != null ? `(${sc.percent}%)` : ""}
              </span>
              <span>{formatCurrency(sc.amount)}</span>
            </div>
          ))}
        </div>

        <div className="my-3 border-t border-dashed border-slate-300" />

        <div className="flex justify-between text-base font-bold">
          <span>{t("billing.grandTotal")}</span>
          <span>{formatCurrency(bill.grand_total)}</span>
        </div>
        <div className="mt-1 flex justify-between text-xs">
          <span>{t("billing.amountPaid")}</span>
          <span>{formatCurrency(bill.amount_paid)}</span>
        </div>
        {bill.grand_total - bill.amount_paid > 0.005 && (
          <div className="flex justify-between text-xs font-semibold text-danger-600">
            <span>{t("billing.remaining")}</span>
            <span>{formatCurrency(bill.grand_total - bill.amount_paid)}</span>
          </div>
        )}

        <p className="mt-4 text-center text-xs text-slate-400">{t("receipt.thankYou")}</p>
      </div>

      <Button variant="secondary" className="mt-4 w-full print:hidden" onClick={() => window.print()}>
        <Printer size={16} />
        {t("receipt.print")}
      </Button>
    </div>
  );
}
