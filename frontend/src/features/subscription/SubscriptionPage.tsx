import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { AlertTriangle, CreditCard } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import { formatCurrency } from "@/lib/format";
import { loadRazorpayCheckout } from "@/lib/loadRazorpayCheckout";
import { parseApiError } from "@/api/errors";
import { useCancelSubscription, useSubscription, useSubscriptionCheckout, useVerifySubscriptionPayment } from "@/features/subscription/hooks";
import { SubscriptionStatusBadge } from "@/features/subscription/components/SubscriptionStatusBadge";
import type { SubscriptionOut } from "@/types/models";

/** States from which starting a fresh checkout makes sense — everything
 * except ACTIVE (which offers Cancel instead) and NOT_CONFIGURED (handled
 * separately as the "first ever subscribe" case, same button either way). */
const RESUBSCRIBE_STATES: SubscriptionOut["status"][] = ["PAYMENT_FAILED", "CANCELLED", "EXPIRED", "PENDING"];

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
}

export function SubscriptionPage() {
  const { t } = useTranslation();
  const { data: subscription, isLoading, isError } = useSubscription();
  const checkout = useSubscriptionCheckout();
  const verify = useVerifySubscriptionPayment();
  const cancel = useCancelSubscription();

  const [error, setError] = useState<string | null>(null);
  const [isOpeningCheckout, setIsOpeningCheckout] = useState(false);

  const handleSubscribe = async () => {
    setError(null);
    setIsOpeningCheckout(true);
    try {
      const order = await checkout.mutateAsync();
      await loadRazorpayCheckout();

      if (!window.Razorpay) {
        throw new Error(t("subscription.checkoutScriptFailed"));
      }

      const razorpay = new window.Razorpay({
        key: order.razorpay_key_id,
        amount: order.amount_paise,
        currency: order.currency,
        order_id: order.razorpay_order_id,
        name: "WhyNotGrace",
        description: t("subscription.checkoutDescription"),
        handler: (response) => {
          verify.mutate(
            {
              subscription_payment_id: order.subscription_payment_id,
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            },
            {
              onSuccess: (result) => {
                if (result.status === "ACTIVE") {
                  toast.success(t("subscription.activated"));
                } else {
                  // Verification call succeeded but the backend didn't
                  // report ACTIVE — never claim success the backend didn't confirm.
                  setError(t("subscription.verificationInconclusive"));
                }
              },
              onError: (err) => setError(parseApiError(err).message),
            }
          );
        },
        modal: {
          ondismiss: () => toast(t("subscription.checkoutDismissed")),
        },
        theme: { color: "#2563eb" },
      });
      razorpay.open();
    } catch (err) {
      const apiError = parseApiError(err);
      setError(apiError.status === 503 ? t("subscription.notConfigured") : apiError.message);
    } finally {
      setIsOpeningCheckout(false);
    }
  };

  const handleCancel = () => {
    if (!window.confirm(t("subscription.confirmCancel"))) return;
    setError(null);
    cancel.mutate(undefined, {
      onSuccess: () => toast.success(t("subscription.cancelled")),
      onError: (err) => setError(parseApiError(err).message),
    });
  };

  const isBusy = checkout.isPending || verify.isPending || isOpeningCheckout;

  return (
    <div>
      <PageHeader title={t("nav.subscription")} subtitle={t("subscription.subtitle")} />

      {isLoading && (
        <div className="flex justify-center py-16">
          <Spinner className="text-brand-600" />
        </div>
      )}

      {isError && (
        <div className="flex flex-col items-center gap-2 py-16 text-danger-600">
          <AlertTriangle size={22} />
          <p className="text-sm font-medium">{t("subscription.loadError")}</p>
        </div>
      )}

      {!isLoading && !isError && subscription && (
        <Card className="max-w-xl p-5">
          {error && (
            <p className="mb-4 rounded-lg border border-danger-500/30 bg-danger-50 px-3 py-2 text-xs text-danger-700">
              {error}
            </p>
          )}

          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                <CreditCard size={20} />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-500">{t("subscription.planName")}</p>
                <p className="text-lg font-bold text-slate-900">
                  {formatCurrency(subscription.amount)}
                  <span className="text-sm font-normal text-slate-500">/{t("subscription.month")}</span>
                </p>
              </div>
            </div>
            <SubscriptionStatusBadge status={subscription.status} />
          </div>

          <div className="mt-4 space-y-2 border-t border-slate-100 pt-4 text-sm">
            {subscription.current_period_start && (
              <div className="flex justify-between">
                <span className="text-slate-500">{t("subscription.startedOn")}</span>
                <span className="font-medium text-slate-800">{formatDate(subscription.current_period_start)}</span>
              </div>
            )}
            {subscription.status === "ACTIVE" && subscription.current_period_end && (
              <div className="flex justify-between">
                <span className="text-slate-500">{t("subscription.nextBillingDate")}</span>
                <span className="font-medium text-slate-800">{formatDate(subscription.current_period_end)}</span>
              </div>
            )}
            {subscription.status === "EXPIRED" && subscription.current_period_end && (
              <div className="flex justify-between">
                <span className="text-slate-500">{t("subscription.expiredOn")}</span>
                <span className="font-medium text-danger-600">{formatDate(subscription.current_period_end)}</span>
              </div>
            )}
            {subscription.status === "CANCELLED" && subscription.cancelled_at && (
              <div className="flex justify-between">
                <span className="text-slate-500">{t("subscription.cancelledOn")}</span>
                <span className="font-medium text-slate-800">{formatDate(subscription.cancelled_at)}</span>
              </div>
            )}
            {subscription.status === "NOT_CONFIGURED" && (
              <p className="text-slate-500">{t("subscription.notSubscribedYet")}</p>
            )}
            {subscription.status === "PAYMENT_FAILED" && (
              <p className="text-danger-600">{t("subscription.lastPaymentFailed")}</p>
            )}
          </div>

          <div className="mt-5">
            {subscription.status === "ACTIVE" ? (
              <Button variant="danger" isLoading={cancel.isPending} onClick={handleCancel}>
                {t("subscription.cancelSubscription")}
              </Button>
            ) : (
              <Button isLoading={isBusy} onClick={() => void handleSubscribe()}>
                {subscription.status === "NOT_CONFIGURED"
                  ? t("subscription.subscribeNow")
                  : RESUBSCRIBE_STATES.includes(subscription.status)
                    ? t("subscription.renewNow")
                    : t("subscription.subscribeNow")}
              </Button>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
