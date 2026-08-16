import { useState } from "react";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { parseApiError } from "@/api/errors";
import { formatCurrency } from "@/lib/format";
import {
  useCancelSubscription,
  useProvisionSubscription,
  useRenewSubscription,
  useSuspendSubscription,
} from "@/features/platform/hooks";
import type { SubscriptionOut } from "@/types/models";

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
}

const STATUS_CLASSES: Record<string, string> = {
  NOT_CONFIGURED: "bg-slate-100 text-slate-600",
  ACTIVE: "bg-success-50 text-success-700",
  GRACE: "bg-warning-50 text-warning-700",
  SUSPENDED: "bg-danger-50 text-danger-600",
  CANCELLED: "bg-slate-100 text-slate-600",
  PAYMENT_FAILED: "bg-danger-50 text-danger-600",
  EXPIRED: "bg-danger-50 text-danger-600",
  PENDING: "bg-slate-100 text-slate-600",
};

export function SubscriptionPanel({
  businessId,
  subscription,
}: {
  businessId: string;
  subscription: SubscriptionOut | undefined;
}) {
  const provision = useProvisionSubscription(businessId);
  const renew = useRenewSubscription(businessId);
  const suspend = useSuspendSubscription(businessId);
  const cancel = useCancelSubscription(businessId);

  const [planName, setPlanName] = useState("POS Only");
  const [amount, setAmount] = useState("600");
  const [months, setMonths] = useState("1");
  const [renewMonths, setRenewMonths] = useState("1");
  const [error, setError] = useState<string | null>(null);

  if (!subscription) return null;

  const handleProvision = async () => {
    setError(null);
    const amountNum = Number(amount);
    const monthsNum = Number(months);
    if (!planName.trim() || !(amountNum >= 0) || !(monthsNum >= 1)) {
      setError("Enter a plan name, an amount of 0 or more, and at least 1 month.");
      return;
    }
    try {
      await provision.mutateAsync({
        plan_name: planName.trim(), amount: amountNum, billing_interval: "monthly", months: monthsNum,
      });
      toast.success("Plan set.");
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const handleRenew = async () => {
    setError(null);
    const monthsNum = Number(renewMonths);
    if (!(monthsNum >= 1)) {
      setError("Enter at least 1 month.");
      return;
    }
    try {
      await renew.mutateAsync({ months: monthsNum });
      toast.success("Renewed.");
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const handleSuspend = async () => {
    if (!window.confirm("Suspend this business's plan immediately? Their dashboard will be blocked.")) return;
    try {
      await suspend.mutateAsync();
      toast.success("Suspended.");
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  const handleCancel = async () => {
    if (!window.confirm("Cancel this business's plan? This ends the relationship — distinct from suspending for non-payment.")) return;
    try {
      await cancel.mutateAsync();
      toast.success("Cancelled.");
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  return (
    <div className="space-y-4">
      {error && (
        <p className="rounded-lg border border-danger-500/30 bg-danger-50 px-3 py-2 text-xs text-danger-700">
          {error}
        </p>
      )}

      <div className="flex items-center justify-between">
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_CLASSES[subscription.status] ?? "bg-slate-100 text-slate-600"}`}
        >
          {subscription.status.replace(/_/g, " ")}
        </span>
        {subscription.amount != null && (
          <span className="text-sm font-semibold text-slate-800">
            {formatCurrency(subscription.amount)}
            <span className="font-normal text-slate-500">/{subscription.billing_interval}</span>
          </span>
        )}
      </div>

      {subscription.plan_name && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-600">
          <span>Plan</span>
          <span className="text-right font-medium text-slate-800">{subscription.plan_name}</span>
          <span>Period start</span>
          <span className="text-right font-medium text-slate-800">{formatDate(subscription.current_period_start)}</span>
          <span>Period end</span>
          <span className="text-right font-medium text-slate-800">{formatDate(subscription.current_period_end)}</span>
        </div>
      )}

      {subscription.status === "NOT_CONFIGURED" || subscription.status === "CANCELLED" ? (
        <div className="space-y-3 border-t border-slate-100 pt-4">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <Label htmlFor="plan-name">Plan name</Label>
              <Input id="plan-name" value={planName} onChange={(e) => setPlanName(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="plan-amount">Amount / mo</Label>
              <Input id="plan-amount" type="number" min={0} value={amount} onChange={(e) => setAmount(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="plan-months">Months</Label>
              <Input id="plan-months" type="number" min={1} value={months} onChange={(e) => setMonths(e.target.value)} />
            </div>
          </div>
          <Button size="sm" isLoading={provision.isPending} onClick={() => void handleProvision()}>
            Set plan
          </Button>
        </div>
      ) : (
        <div className="flex flex-wrap items-end gap-3 border-t border-slate-100 pt-4">
          <div>
            <Label htmlFor="renew-months">Renew (months)</Label>
            <Input
              id="renew-months"
              type="number"
              min={1}
              className="w-24"
              value={renewMonths}
              onChange={(e) => setRenewMonths(e.target.value)}
            />
          </div>
          <Button size="sm" isLoading={renew.isPending} onClick={() => void handleRenew()}>
            Renew
          </Button>
          {subscription.status !== "SUSPENDED" && (
            <Button size="sm" variant="danger" isLoading={suspend.isPending} onClick={() => void handleSuspend()}>
              Suspend
            </Button>
          )}
          <Button size="sm" variant="ghost" isLoading={cancel.isPending} onClick={() => void handleCancel()}>
            Cancel plan
          </Button>
        </div>
      )}
    </div>
  );
}
