import { useState } from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle, Gift, Plus } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import { Switch } from "@/components/ui/Switch";
import { useAuthStore } from "@/stores/authStore";
import { useLoyaltyRules, useUpdateLoyaltyRule } from "@/features/loyalty/hooks";
import { RuleFormDialog } from "@/features/loyalty/components/RuleFormDialog";

export function LoyaltyPage() {
  const { t } = useTranslation();
  const role = useAuthStore((s) => s.user?.role);
  const canManage = role === "OWNER";
  const { data: rules, isLoading, isError } = useLoyaltyRules();
  const updateRule = useUpdateLoyaltyRule();
  const [formOpen, setFormOpen] = useState(false);

  return (
    <div>
      <PageHeader
        title={t("nav.loyalty")}
        subtitle={t("loyaltyAdmin.subtitle")}
        actions={
          canManage && (
            <Button onClick={() => setFormOpen(true)}>
              <Plus size={16} />
              {t("loyaltyAdmin.addRule")}
            </Button>
          )
        }
      />

      {isLoading && (
        <div className="flex justify-center py-16">
          <Spinner className="text-brand-600" />
        </div>
      )}

      {isError && (
        <div className="flex flex-col items-center gap-2 py-16 text-danger-600">
          <AlertTriangle size={22} />
          <p className="text-sm font-medium">{t("loyaltyAdmin.loadError")}</p>
        </div>
      )}

      {!isLoading && !isError && (rules ?? []).length === 0 && (
        <div className="flex flex-col items-center gap-2 py-16 text-center text-slate-400">
          <Gift size={24} />
          <p className="text-sm">{t("loyaltyAdmin.noRules")}</p>
        </div>
      )}

      {!isLoading && !isError && (rules ?? []).length > 0 && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {(rules ?? []).map((rule) => (
            <Card key={rule.id} className={`p-4 ${!rule.is_active ? "opacity-60" : ""}`}>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-bold text-slate-900">{rule.name}</p>
                  <p className="text-xs text-slate-500">{t(`loyaltyAdmin.ruleTypeLabel.${rule.rule_type}`)}</p>
                </div>
                {canManage && (
                  <Switch
                    checked={rule.is_active}
                    onChange={(checked) => updateRule.mutate({ ruleId: rule.id, payload: { is_active: checked } })}
                    label={t("menuAdmin.isActive")}
                  />
                )}
              </div>
              <p className="mt-2 text-sm text-slate-600">
                {t("loyaltyAdmin.thresholdLabel")}: <span className="font-semibold">{rule.threshold}</span>
              </p>
              <p className="text-sm text-slate-600">
                {t("loyaltyAdmin.rewardLabel")}: <span className="font-semibold">{t(`loyaltyAdmin.rewardType.${rule.reward_type}`)}</span>
                {rule.reward_value != null && ` (${rule.reward_value})`}
              </p>
              {rule.description && <p className="mt-1.5 text-xs text-slate-400">{rule.description}</p>}
            </Card>
          ))}
        </div>
      )}

      {canManage && <RuleFormDialog open={formOpen} onClose={() => setFormOpen(false)} />}
    </div>
  );
}
