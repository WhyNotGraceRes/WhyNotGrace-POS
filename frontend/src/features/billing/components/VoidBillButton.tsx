import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { Ban } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { parseApiError } from "@/api/errors";
import { useVoidBill } from "@/features/billing/hooks";
import type { BillOut } from "@/types/models";

/** Cancels the entire bill — the backend allows this whether or not it's
 * already paid (see billing_service.void_bill), for the rare "this whole
 * invoice was a mistake" case. Distinct from a refund: no money moves,
 * this only marks the invoice cancelled and frees the table. Whether a
 * cashier or only a manager can do this is enforced server-side by the
 * void_requires_manager toggle — this button doesn't duplicate that
 * check, it just surfaces whatever the server says. */
export function VoidBillButton({ bill }: { bill: BillOut }) {
  const { t } = useTranslation();
  const voidBill = useVoidBill();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (bill.status === "CANCELLED") return null;

  const submit = () => {
    setError(null);
    voidBill.mutate(
      { billId: bill.id, reason: reason.trim() || undefined },
      {
        onSuccess: () => {
          toast.success(t("billing.billVoided"));
          setOpen(false);
          setReason("");
        },
        onError: (err) => setError(parseApiError(err).message),
      }
    );
  };

  if (!open) {
    return (
      <Button variant="ghost" size="sm" onClick={() => setOpen(true)}>
        <Ban size={15} className="mr-1.5" />
        {t("billing.voidBill")}
      </Button>
    );
  }

  return (
    <div className="w-full rounded-lg border border-danger-200 bg-danger-50/40 p-3">
      <p className="mb-2 text-sm text-stone-700">
        {t("billing.voidBillConfirm", { number: bill.bill_number })}
      </p>
      {error && <p className="mb-2 text-xs text-danger-600">{error}</p>}
      <Input
        value={reason}
        autoFocus
        placeholder={t("billing.voidReasonPlaceholder")}
        onChange={(e) => setReason(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") submit();
          if (e.key === "Escape") setOpen(false);
        }}
      />
      <div className="mt-2 flex gap-2">
        <Button size="sm" variant="danger" isLoading={voidBill.isPending} onClick={submit}>
          {t("billing.voidBill")}
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
          {t("common.cancel")}
        </Button>
      </div>
    </div>
  );
}
