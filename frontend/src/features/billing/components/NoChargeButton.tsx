import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { HandCoins } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { parseApiError } from "@/api/errors";
import { formatCurrency } from "@/lib/format";
import { useMarkBillNoCharge } from "@/features/billing/hooks";
import type { BillOut } from "@/types/models";

/** Marks the whole bill no-charge — a staff meal, or a table the owner
 * decided not to bill. Settles it at zero without taking a payment. */
export function NoChargeButton({ bill }: { bill: BillOut }) {
  const { t } = useTranslation();
  const markNoCharge = useMarkBillNoCharge();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Already settled, cancelled, or already no-charge: nothing to offer.
  if (bill.status === "PAID" || bill.status === "CANCELLED" || bill.nc_at) return null;
  // Once money is on the bill the server refuses this, so don't offer it.
  if (bill.amount_paid > 0) return null;

  const submit = () => {
    setError(null);
    markNoCharge.mutate(
      { billId: bill.id, reason: reason.trim() || undefined },
      {
        onSuccess: () => {
          toast.success(t("billing.markedNoCharge"));
          setOpen(false);
          setReason("");
        },
        onError: (err) => setError(parseApiError(err).message),
      }
    );
  };

  if (!open) {
    return (
      <Button variant="secondary" size="sm" onClick={() => setOpen(true)}>
        <HandCoins size={15} className="mr-1.5" />
        {t("billing.markNoCharge")}
      </Button>
    );
  }

  return (
    <div className="w-full rounded-lg border border-stone-200 p-3">
      <p className="mb-2 text-sm text-stone-700">
        {t("billing.markNoChargeConfirm", { amount: formatCurrency(bill.grand_total) })}
      </p>
      {error && <p className="mb-2 text-xs text-danger-600">{error}</p>}
      <Input
        value={reason}
        autoFocus
        placeholder={t("billing.ncReasonPlaceholder")}
        onChange={(e) => setReason(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") submit();
          if (e.key === "Escape") setOpen(false);
        }}
      />
      <div className="mt-2 flex gap-2">
        <Button size="sm" isLoading={markNoCharge.isPending} onClick={submit}>
          {t("billing.markNoCharge")}
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
          {t("common.cancel")}
        </Button>
      </div>
    </div>
  );
}
