import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { AlertTriangle, Lock, Printer } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Spinner } from "@/components/ui/Spinner";
import { apiClient } from "@/api/client";
import { parseApiError } from "@/api/errors";
import { formatCurrencyExact } from "@/lib/format";
import {
  useCloseShift,
  useCurrentShift,
  useOpenShift,
  useShiftReport,
} from "@/features/shifts/hooks";
import type { ShiftReportOut } from "@/types/models";

export function ShiftPage() {
  const { t } = useTranslation();
  const { data: shift, isLoading } = useCurrentShift();
  const { data: report } = useShiftReport(shift?.id ?? null);
  const openShift = useOpenShift();
  const closeShift = useCloseShift();

  const [float, setFloat] = useState("0");
  const [counted, setCounted] = useState("");
  const [notes, setNotes] = useState("");
  const [closed, setClosed] = useState<ShiftReportOut | null>(null);

  const handleOpen = async () => {
    try {
      await openShift.mutateAsync(Number(float) || 0);
      toast.success(t("shift.opened"));
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  const handleClose = async () => {
    if (!shift) return;
    try {
      const result = await closeShift.mutateAsync({
        shiftId: shift.id,
        payload: { declared_cash: Number(counted) || 0, notes: notes.trim() || null },
      });
      // Held in local state rather than read back from the list: this is the
      // one moment the cashier sees the variance, and it must not vanish on
      // the next refetch.
      setClosed(result);
      setCounted("");
      setNotes("");
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  const handlePrint = async (shiftId: string) => {
    const { printHtmlDocument } = await import("@/lib/printReceipt");
    try {
      const { data } = await apiClient.get<string>(`/shifts/${shiftId}/report/print`, {
        params: { format: "html" },
        responseType: "text",
      });
      await printHtmlDocument(data);
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner className="text-brand-600" />
      </div>
    );
  }

  return (
    <div>
      <PageHeader title={t("shift.title")} subtitle={t("shift.subtitle")} />

      {closed && <ClosedSummary report={closed} onDismiss={() => setClosed(null)} onPrint={handlePrint} />}

      {!shift && !closed && (
        <Card className="max-w-md space-y-4 p-5">
          <div>
            <h2 className="text-sm font-semibold text-stone-900">{t("shift.openTitle")}</h2>
            <p className="mt-0.5 text-xs text-stone-500">{t("shift.openHint")}</p>
          </div>
          <div>
            <Label htmlFor="shift-float">{t("shift.openingFloat")}</Label>
            <Input
              id="shift-float"
              type="number"
              min={0}
              step="0.01"
              value={float}
              onChange={(e) => setFloat(e.target.value)}
            />
          </div>
          <Button isLoading={openShift.isPending} onClick={() => void handleOpen()}>
            {t("shift.open")}
          </Button>
        </Card>
      )}

      {shift && (
        <div className="max-w-md space-y-4">
          {report && <RunningTotals report={report} />}

          <Card className="space-y-4 p-5">
            <div>
              <h2 className="text-sm font-semibold text-stone-900">{t("shift.closeTitle")}</h2>
              {/* The instruction is the control. A cashier who reads the
                  expected figure first will type it back. */}
              <p className="mt-0.5 text-xs text-stone-500">
                {report?.blind_count ? t("shift.closeHintBlind") : t("shift.closeHint")}
              </p>
            </div>

            <div>
              <Label htmlFor="shift-counted">{t("shift.countedCash")}</Label>
              <Input
                id="shift-counted"
                type="number"
                min={0}
                step="0.01"
                value={counted}
                onChange={(e) => setCounted(e.target.value)}
                placeholder="0.00"
              />
            </div>

            <div>
              <Label htmlFor="shift-notes">{t("shift.notes")}</Label>
              <Input id="shift-notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
            </div>

            <Button
              isLoading={closeShift.isPending}
              disabled={counted.trim() === ""}
              onClick={() => void handleClose()}
            >
              {t("shift.close")}
            </Button>
          </Card>
        </div>
      )}
    </div>
  );
}

function RunningTotals({ report }: { report: ShiftReportOut }) {
  const { t } = useTranslation();
  return (
    <Card className="space-y-3 p-5">
      <h2 className="text-sm font-semibold text-stone-900">{t("shift.currentTitle")}</h2>

      <dl className="space-y-1 text-sm">
        <Row label={t("shift.openingFloat")} value={formatCurrencyExact(report.opening_float)} />
        {report.payments.map((line) => (
          <Row
            key={line.method}
            label={`${line.method} ×${line.count}`}
            value={formatCurrencyExact(line.amount)}
          />
        ))}
        <Row label={t("shift.grossTakings")} value={formatCurrencyExact(report.gross_takings)} bold />
        {report.refunds_count > 0 && (
          <Row label={t("shift.refunds")} value={`-${formatCurrencyExact(report.refunds_total)}`} />
        )}
        <Row label={t("shift.billsSettled")} value={String(report.bills_settled)} />
        {report.bills_voided > 0 && (
          <Row label={t("shift.billsVoided")} value={String(report.bills_voided)} tone="warn" />
        )}
      </dl>

      {/* Withheld deliberately, and said so — an empty space would read as a
          bug rather than as a control. */}
      {report.blind_count && report.expected_cash === null && (
        <p className="flex items-start gap-1.5 rounded bg-stone-50 px-2 py-1.5 text-xs text-stone-600">
          <Lock size={12} className="mt-0.5 shrink-0" />
          {t("shift.expectedHidden")}
        </p>
      )}
      {report.expected_cash !== null && (
        <Row label={t("shift.expectedCash")} value={formatCurrencyExact(report.expected_cash)} bold />
      )}
    </Card>
  );
}

function ClosedSummary({
  report,
  onDismiss,
  onPrint,
}: {
  report: ShiftReportOut;
  onDismiss: () => void;
  onPrint: (shiftId: string) => Promise<void>;
}) {
  const { t } = useTranslation();
  const variance = report.variance ?? 0;
  const balanced = Math.abs(variance) < 0.005;

  return (
    <Card className="mb-4 max-w-md space-y-4 p-5">
      <h2 className="text-sm font-semibold text-stone-900">{t("shift.closedTitle")}</h2>

      <dl className="space-y-1 text-sm">
        <Row label={t("shift.expectedCash")} value={formatCurrencyExact(report.expected_cash ?? 0)} />
        <Row label={t("shift.countedCash")} value={formatCurrencyExact(report.declared_cash ?? 0)} />
      </dl>

      {/* The one line an owner actually reads. */}
      <div
        className={
          balanced
            ? "rounded-lg bg-brand-50 px-3 py-2 text-sm font-semibold text-brand-700"
            : "rounded-lg bg-danger-50 px-3 py-2 text-sm font-semibold text-danger-700"
        }
      >
        {balanced ? (
          t("shift.balanced")
        ) : (
          <span className="flex items-center gap-1.5">
            <AlertTriangle size={15} />
            {variance < 0
              ? t("shift.short", { amount: formatCurrencyExact(Math.abs(variance)) })
              : t("shift.over", { amount: formatCurrencyExact(variance) })}
          </span>
        )}
      </div>

      <div className="flex gap-2">
        <Button onClick={() => void onPrint(report.shift_id)}>
          <Printer size={15} /> {t("shift.printReport")}
        </Button>
        <Button variant="secondary" onClick={onDismiss}>
          {t("common.done")}
        </Button>
      </div>
    </Card>
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
  tone?: "warn";
}) {
  return (
    <div className="flex justify-between">
      <dt className={tone === "warn" ? "text-amber-700" : "text-stone-600"}>{label}</dt>
      <dd className={bold ? "font-semibold text-stone-900" : "text-stone-800"}>{value}</dd>
    </div>
  );
}
