import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { Banknote, CreditCard, Smartphone, Wifi } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { cn } from "@/lib/cn";
import { formatCurrency } from "@/lib/format";
import { parseApiError } from "@/api/errors";
import { useRecordManualPayment, useCreateRazorpayOrder } from "@/features/payments/hooks";
import type { BillOut, PaymentMethod } from "@/types/models";

const TABS: { method: PaymentMethod; icon: typeof Banknote; labelKey: string }[] = [
  { method: "CASH", icon: Banknote, labelKey: "payment.cash" },
  { method: "UPI", icon: Smartphone, labelKey: "payment.upi" },
  { method: "CARD", icon: CreditCard, labelKey: "payment.card" },
  { method: "ONLINE", icon: Wifi, labelKey: "payment.online" },
];

export function PaymentPanel({ bill }: { bill: BillOut }) {
  const { t } = useTranslation();
  const remaining = Math.max(0, Math.round((bill.grand_total - bill.amount_paid) * 100) / 100);

  const [tab, setTab] = useState<PaymentMethod>("CASH");
  const [amount, setAmount] = useState(String(remaining));
  const [received, setReceived] = useState(String(remaining));
  const [receivedTouched, setReceivedTouched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [razorpayNotice, setRazorpayNotice] = useState<string | null>(null);

  const recordManual = useRecordManualPayment();
  const createRazorpayOrder = useCreateRazorpayOrder();

  const amountNumber = Number(amount);
  const changeToReturn = Math.max(0, Number(received) - amountNumber);

  // Whenever the real remaining balance changes (a payment just landed and
  // the bill refetched), default the fields to the new remaining amount
  // rather than leaving stale figures from the payment that just happened.
  useEffect(() => {
    setAmount(String(remaining));
    setReceived(String(remaining));
    setReceivedTouched(false);
  }, [remaining]);

  const handleManualConfirm = () => {
    setError(null);
    if (!(amountNumber > 0)) {
      setError(t("payment.invalidAmount"));
      return;
    }
    recordManual.mutate(
      { bill_id: bill.id, amount: amountNumber, method: tab },
      {
        onSuccess: () => toast.success(t("payment.recorded")),
        onError: (err) => setError(parseApiError(err).message),
      }
    );
  };

  const handleRazorpay = () => {
    setError(null);
    setRazorpayNotice(null);
    createRazorpayOrder.mutate(
      { payload: { bill_id: bill.id }, idempotencyKey: `${bill.id}-${Date.now()}` },
      {
        onSuccess: (order) => {
          // Real backend contract stops here for this phase — actually
          // collecting payment requires loading Razorpay's Checkout widget,
          // which is out of scope. Never claim payment succeeded from just
          // having an order id.
          setRazorpayNotice(
            t("payment.razorpayOrderCreated", { orderId: order.razorpay_order_id, amount: formatCurrency(order.amount_paise / 100) })
          );
        },
        onError: (err) => {
          const apiError = parseApiError(err);
          setError(
            apiError.status === 503 ? t("payment.razorpayNotConfigured") : apiError.message
          );
        },
      }
    );
  };

  if (bill.status === "PAID" || bill.status === "CANCELLED") {
    return null;
  }

  return (
    <div>
      <div className="mb-3 flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
        <span className="text-sm text-slate-500">{t("billing.remaining")}</span>
        <span className="text-lg font-bold text-slate-900">{formatCurrency(remaining)}</span>
      </div>

      <div className="mb-3 grid grid-cols-4 gap-1.5">
        {TABS.map(({ method, icon: Icon, labelKey }) => (
          <button
            key={method}
            type="button"
            onClick={() => {
              setTab(method);
              setError(null);
              setRazorpayNotice(null);
              setAmount(String(remaining));
              setReceived(String(remaining));
              setReceivedTouched(false);
            }}
            className={cn(
              "flex flex-col items-center gap-1 rounded-lg border px-2 py-2 text-xs font-semibold transition-colors focus-ring",
              tab === method ? "border-brand-500 bg-brand-50 text-brand-700" : "border-slate-200 text-slate-600 hover:bg-slate-50"
            )}
          >
            <Icon size={16} />
            {t(labelKey)}
          </button>
        ))}
      </div>

      {error && (
        <p className="mb-3 rounded-lg border border-danger-500/30 bg-danger-50 px-3 py-2 text-xs text-danger-700">
          {error}
        </p>
      )}

      {tab === "ONLINE" ? (
        <div>
          {razorpayNotice && (
            <p className="mb-3 rounded-lg border border-brand-500/30 bg-brand-50 px-3 py-2 text-xs text-brand-700">
              {razorpayNotice}
            </p>
          )}
          <Button className="w-full" isLoading={createRazorpayOrder.isPending} onClick={handleRazorpay}>
            {t("payment.payOnline")}
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div>
            <Label htmlFor="pay-amount">{t("payment.amount")}</Label>
            <Input
              id="pay-amount"
              type="number"
              min={0.01}
              step="0.01"
              value={amount}
              onChange={(e) => {
                setAmount(e.target.value);
                // "Amount received" tracks the charged amount by default (the
                // common case: customer pays exactly what's being charged,
                // whether that's the full remaining balance or a deliberate
                // partial payment) until the cashier explicitly overrides it
                // to record a different tendered amount.
                if (!receivedTouched) {
                  setReceived(e.target.value);
                }
              }}
            />
          </div>

          {tab === "CASH" && (
            <div>
              <Label htmlFor="pay-received">{t("payment.amountReceived")}</Label>
              <Input
                id="pay-received"
                type="number"
                min={0}
                step="0.01"
                value={received}
                onChange={(e) => {
                  setReceivedTouched(true);
                  setReceived(e.target.value);
                }}
              />
              {changeToReturn > 0 && (
                <p className="mt-1.5 text-sm font-semibold text-success-700">
                  {t("payment.changeToReturn")}: {formatCurrency(changeToReturn)}
                </p>
              )}
            </div>
          )}

          <Button
            size="lg"
            className="w-full"
            isLoading={recordManual.isPending}
            onClick={handleManualConfirm}
          >
            {t("payment.confirmPayment")}
          </Button>
        </div>
      )}
    </div>
  );
}
