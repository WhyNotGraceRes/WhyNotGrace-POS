import { useTranslation } from "react-i18next";
import { Gift, Info } from "lucide-react";
import toast from "react-hot-toast";
import { Dialog } from "@/components/ui/Dialog";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import { formatCurrency, formatNumber } from "@/lib/format";
import { parseApiError } from "@/api/errors";
import { useAuthStore } from "@/stores/authStore";
import { useIsFeatureEnabled } from "@/features/settings/hooks";
import { useLoyaltyAccount, useLoyaltyRewards, useRedeemReward } from "@/features/loyalty/hooks";
import type { CustomerOut } from "@/types/models";

const LOYALTY_VIEW_ROLES = new Set(["OWNER", "MANAGER"]);

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-slate-100 py-2.5 last:border-0">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="text-sm font-medium text-slate-800">{children}</span>
    </div>
  );
}

export function CustomerDetailDialog({ customer, onClose }: { customer: CustomerOut | null; onClose: () => void }) {
  const { t } = useTranslation();
  const role = useAuthStore((s) => s.user?.role);
  const loyaltyEnabled = useIsFeatureEnabled("LOYALTY");
  const canViewLoyalty = Boolean(role && LOYALTY_VIEW_ROLES.has(role)) && loyaltyEnabled;

  const { data: account, isLoading: accountLoading, isError: accountError } = useLoyaltyAccount(
    customer?.id ?? null,
    { enabled: canViewLoyalty && Boolean(customer) }
  );
  const { data: rewards } = useLoyaltyRewards(customer?.id ?? null, { enabled: canViewLoyalty && Boolean(customer) });
  const redeemReward = useRedeemReward();
  const unredeemedRewards = rewards?.filter((r) => !r.is_redeemed) ?? [];

  const handleRedeem = (rewardId: string) => {
    redeemReward.mutate(
      { rewardId, payload: {} },
      {
        onSuccess: () => toast.success(t("customers.rewardRedeemed")),
        onError: (err) => toast.error(parseApiError(err).message),
      }
    );
  };

  if (!customer) return null;

  return (
    <Dialog open={Boolean(customer)} onClose={onClose} title={t("customers.details")}>
      <div>
        <Row label={t("customers.firstName")}>{customer.first_name}</Row>
        <Row label={t("customers.mobile")}>{customer.mobile}</Row>
        {customer.email && <Row label={t("customers.email")}>{customer.email}</Row>}
        {customer.birthday && <Row label={t("customers.birthday")}>{customer.birthday}</Row>}
      </div>

      {canViewLoyalty && (
        <div className="mt-4 rounded-lg border border-slate-100 p-3">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <Gift size={14} />
            {t("customers.loyalty")}
          </p>

          {accountLoading && (
            <div className="flex justify-center py-3">
              <Spinner size={16} className="text-brand-600" />
            </div>
          )}

          {accountError && <p className="text-sm text-slate-400">{t("customers.loyaltyNotEnrolled")}</p>}

          {account && (
            <div>
              <Row label={t("customers.totalOrders")}>{formatNumber(account.total_orders)}</Row>
              <Row label={t("customers.totalSpend")}>{formatCurrency(account.total_spend)}</Row>
              <Row label={t("customers.pointsBalance")}>{formatNumber(account.points_balance)}</Row>
              {unredeemedRewards.length > 0 && (
                <div className="mt-2 space-y-1.5">
                  <p className="text-xs font-semibold text-accent-700">
                    {t("customers.unredeemedRewards", { count: unredeemedRewards.length })}
                  </p>
                  {unredeemedRewards.map((reward) => (
                    <div key={reward.id} className="flex items-center justify-between gap-2 rounded-lg bg-accent-50 px-2.5 py-1.5">
                      <span className="text-xs text-accent-800">
                        {t(`loyaltyAdmin.rewardType.${reward.reward_type}`)}
                        {reward.reward_value != null && ` · ${reward.reward_value}`}
                      </span>
                      <Button
                        size="sm"
                        variant="secondary"
                        isLoading={redeemReward.isPending}
                        onClick={() => handleRedeem(reward.id)}
                      >
                        {t("customers.redeem")}
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="mt-4 flex items-start gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">
        <Info size={13} className="mt-0.5 shrink-0" />
        <p>{t("customers.noCustomerHistoryNote")}</p>
      </div>
    </Dialog>
  );
}
