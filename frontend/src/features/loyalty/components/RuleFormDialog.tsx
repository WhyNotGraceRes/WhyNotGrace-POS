import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";

import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { parseApiError } from "@/api/errors";
import { useCreateLoyaltyRule } from "@/features/loyalty/hooks";

const RULE_TYPES = ["ORDER_COUNT_THRESHOLD", "SPEND_THRESHOLD", "POINTS_PER_AMOUNT", "CUSTOM"] as const;
const REWARD_TYPES = ["FREE_ITEM", "DISCOUNT_PERCENT", "DISCOUNT_AMOUNT", "POINTS"] as const;

export function RuleFormDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const createRule = useCreateLoyaltyRule();

  const [name, setName] = useState("");
  const [ruleType, setRuleType] = useState<(typeof RULE_TYPES)[number]>("SPEND_THRESHOLD");
  const [threshold, setThreshold] = useState("");
  const [rewardType, setRewardType] = useState<(typeof REWARD_TYPES)[number]>("POINTS");
  const [rewardValue, setRewardValue] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setError(null);
    const thresholdNum = Number(threshold);
    if (!name.trim() || !(thresholdNum > 0)) {
      setError(t("loyaltyAdmin.ruleFieldsInvalid"));
      return;
    }
    try {
      await createRule.mutateAsync({
        name: name.trim(),
        rule_type: ruleType,
        threshold: thresholdNum,
        reward_type: rewardType,
        reward_value: rewardValue ? Number(rewardValue) : undefined,
        description: description.trim() || undefined,
      });
      toast.success(t("loyaltyAdmin.ruleCreated"));
      setName("");
      setThreshold("");
      setRewardValue("");
      setDescription("");
      onClose();
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title={t("loyaltyAdmin.addRule")} size="sm">
      <div className="space-y-3">
        {error && <p className="text-xs text-danger-600">{error}</p>}
        <div>
          <Label htmlFor="rule-name">{t("menuAdmin.name")}</Label>
          <Input id="rule-name" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="rule-type">{t("loyaltyAdmin.ruleType")}</Label>
          <Select id="rule-type" value={ruleType} onChange={(e) => setRuleType(e.target.value as typeof ruleType)}>
            {RULE_TYPES.map((rt) => (
              <option key={rt} value={rt}>
                {t(`loyaltyAdmin.ruleTypeLabel.${rt}`)}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label htmlFor="rule-threshold">{t("loyaltyAdmin.threshold")}</Label>
          <Input id="rule-threshold" type="number" min={0.01} step="0.01" value={threshold} onChange={(e) => setThreshold(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="rule-reward-type">{t("loyaltyAdmin.rewardTypeLabel")}</Label>
          <Select id="rule-reward-type" value={rewardType} onChange={(e) => setRewardType(e.target.value as typeof rewardType)}>
            {REWARD_TYPES.map((rt) => (
              <option key={rt} value={rt}>
                {t(`loyaltyAdmin.rewardType.${rt}`)}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label htmlFor="rule-reward-value">{t("loyaltyAdmin.rewardValue")}</Label>
          <Input id="rule-reward-value" type="number" step="0.01" value={rewardValue} onChange={(e) => setRewardValue(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="rule-desc">{t("menuAdmin.description")}</Label>
          <Input id="rule-desc" value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <Button className="w-full" isLoading={createRule.isPending} onClick={() => void handleSubmit()}>
          {t("loyaltyAdmin.addRule")}
        </Button>
      </div>
    </Dialog>
  );
}
