import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { cn } from "@/lib/cn";
import { parseApiError } from "@/api/errors";
import { useApplyDiscount } from "@/features/billing/hooks";
import type { BillOut } from "@/types/models";

export function DiscountForm({ bill }: { bill: BillOut }) {
  const { t } = useTranslation();
  const applyDiscount = useApplyDiscount();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [mode, setMode] = useState<"percent" | "amount">("percent");
  const [value, setValue] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleApply = () => {
    setError(null);
    const numeric = Number(value);
    if (!name.trim() || !(numeric > 0)) {
      setError(t("billing.discountInvalid"));
      return;
    }
    applyDiscount.mutate(
      {
        billId: bill.id,
        payload: {
          name: name.trim(),
          percent: mode === "percent" ? numeric : undefined,
          amount: mode === "amount" ? numeric : undefined,
          reason: reason.trim() || undefined,
        },
      },
      {
        onSuccess: () => {
          toast.success(t("billing.discountApplied"));
          setOpen(false);
          setName("");
          setValue("");
          setReason("");
        },
        onError: (err) => setError(parseApiError(err).message),
      }
    );
  };

  if (bill.status === "PAID" || bill.status === "CANCELLED") return null;

  if (!open) {
    return (
      <Button variant="secondary" size="sm" onClick={() => setOpen(true)}>
        {t("billing.applyDiscount")}
      </Button>
    );
  }

  return (
    <div className="w-full rounded-lg border border-slate-200 p-3">
      {error && <p className="mb-2 text-xs text-danger-600">{error}</p>}
      <div className="space-y-2">
        <div>
          <Label htmlFor="discount-name">{t("billing.discountName")}</Label>
          <Input id="discount-name" value={name} onChange={(e) => setName(e.target.value)} />
        </div>

        <div className="flex gap-1.5">
          <button
            type="button"
            onClick={() => setMode("percent")}
            className={cn(
              "flex-1 rounded-lg border px-2 py-1.5 text-xs font-semibold",
              mode === "percent" ? "border-brand-500 bg-brand-50 text-brand-700" : "border-slate-200 text-slate-500"
            )}
          >
            {t("billing.percent")}
          </button>
          <button
            type="button"
            onClick={() => setMode("amount")}
            className={cn(
              "flex-1 rounded-lg border px-2 py-1.5 text-xs font-semibold",
              mode === "amount" ? "border-brand-500 bg-brand-50 text-brand-700" : "border-slate-200 text-slate-500"
            )}
          >
            {t("billing.flatAmount")}
          </button>
        </div>

        <div>
          <Label htmlFor="discount-value">{mode === "percent" ? t("billing.percent") : t("billing.flatAmount")}</Label>
          <Input
            id="discount-value"
            type="number"
            min={0}
            max={mode === "percent" ? 100 : undefined}
            step="0.01"
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
        </div>

        <div>
          <Label htmlFor="discount-reason">{t("billing.discountReason")}</Label>
          <Input id="discount-reason" value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>

        <div className="flex gap-2 pt-1">
          <Button size="sm" isLoading={applyDiscount.isPending} onClick={handleApply}>
            {t("billing.applyDiscount")}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
            {t("common.cancel")}
          </Button>
        </div>
      </div>
    </div>
  );
}
