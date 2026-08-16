import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { Ban } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { parseApiError } from "@/api/errors";
import { formatCurrency } from "@/lib/format";
import { useVoidBillItem } from "@/features/billing/hooks";
import type { BillItemOut, BillOut } from "@/types/models";

export function BillItemsList({ bill }: { bill: BillOut }) {
  const { t } = useTranslation();
  const [voidingId, setVoidingId] = useState<string | null>(null);

  const isOpen = bill.status !== "PAID" && bill.status !== "CANCELLED";

  return (
    <ul className="divide-y divide-slate-100 rounded-lg border border-slate-100">
      {bill.items.map((item) =>
        voidingId === item.id ? (
          <VoidItemRow
            key={item.id}
            bill={bill}
            item={item}
            onDone={() => setVoidingId(null)}
            onCancel={() => setVoidingId(null)}
          />
        ) : (
          <li key={item.id} className="flex items-center justify-between gap-2 px-3 py-2 text-sm">
            <span className={item.voided_at ? "text-slate-400 line-through" : "text-slate-700"}>
              {item.quantity} × {item.item_name_snapshot}
            </span>

            <span className="flex items-center gap-2">
              {item.voided_at && (
                // The struck line stays visible to the cashier. It is not on
                // the guest's printed bill and not in the total, but a line
                // that vanished entirely would look like the void had failed.
                <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs font-medium text-slate-500">
                  {item.void_reason ? `${t("billing.voided")}: ${item.void_reason}` : t("billing.voided")}
                </span>
              )}
              <span
                className={
                  item.voided_at ? "text-slate-400 line-through" : "font-semibold text-slate-800"
                }
              >
                {formatCurrency(item.line_total)}
              </span>
              {isOpen && !item.voided_at && (
                <button
                  type="button"
                  onClick={() => setVoidingId(item.id)}
                  aria-label={t("billing.voidItem")}
                  title={t("billing.voidItem")}
                  className="rounded p-1 text-slate-400 hover:bg-danger-50 hover:text-danger-600"
                >
                  <Ban size={15} />
                </button>
              )}
            </span>
          </li>
        )
      )}
    </ul>
  );
}

function VoidItemRow({
  bill,
  item,
  onDone,
  onCancel,
}: {
  bill: BillOut;
  item: BillItemOut;
  onDone: () => void;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const voidItem = useVoidBillItem();
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Whether a reason is mandatory, and whether this user is senior enough,
  // are both decided by the server according to the counter's toggles. The
  // form always offers the field and surfaces whatever the server says,
  // rather than keeping a second copy of those rules here that could drift.
  const submit = () => {
    setError(null);
    voidItem.mutate(
      { billId: bill.id, itemId: item.id, reason: reason.trim() || undefined },
      {
        onSuccess: () => {
          toast.success(t("billing.itemVoided"));
          onDone();
        },
        onError: (err) => setError(parseApiError(err).message),
      }
    );
  };

  return (
    <li className="space-y-2 bg-slate-50 px-3 py-2.5 text-sm">
      <p className="text-slate-700">
        {t("billing.voidItemConfirm", {
          item: `${item.quantity} × ${item.item_name_snapshot}`,
        })}
      </p>
      {error && <p className="text-xs text-danger-600">{error}</p>}
      <Input
        value={reason}
        autoFocus
        placeholder={t("billing.voidReasonPlaceholder")}
        onChange={(e) => setReason(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") submit();
          if (e.key === "Escape") onCancel();
        }}
      />
      <div className="flex gap-2">
        <Button size="sm" variant="danger" isLoading={voidItem.isPending} onClick={submit}>
          {t("billing.voidItem")}
        </Button>
        <Button size="sm" variant="ghost" onClick={onCancel}>
          {t("common.cancel")}
        </Button>
      </div>
    </li>
  );
}
