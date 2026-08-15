import { useTranslation } from "react-i18next";
import { AlertTriangle } from "lucide-react";
import toast from "react-hot-toast";

import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { Switch } from "@/components/ui/Switch";
import { parseApiError } from "@/api/errors";
import { useFeatureFlags, useUpdateFeatureFlag } from "@/features/settings/hooks";
import type { FeatureModule } from "@/types/models";

const ALWAYS_ON: FeatureModule[] = ["CORE_POS"];

export function FeatureFlagsPage() {
  const { t } = useTranslation();
  const { data: flags, isLoading, isError } = useFeatureFlags();
  const updateFlag = useUpdateFeatureFlag();

  const handleToggle = (module: FeatureModule, enabled: boolean) => {
    updateFlag.mutate(
      { module, enabled },
      {
        onSuccess: () => toast.success(enabled ? t("featureFlags.enabled", { module: t(`featureModule.${module}`) }) : t("featureFlags.disabled", { module: t(`featureModule.${module}`) })),
        onError: (err) => toast.error(parseApiError(err).message),
      }
    );
  };

  return (
    <div>
      <PageHeader title={t("nav.featureFlags")} subtitle={t("featureFlags.subtitle")} />

      {isLoading && (
        <div className="flex justify-center py-16">
          <Spinner className="text-brand-600" />
        </div>
      )}

      {isError && (
        <div className="flex flex-col items-center gap-2 py-16 text-danger-600">
          <AlertTriangle size={22} />
          <p className="text-sm font-medium">{t("featureFlags.loadError")}</p>
        </div>
      )}

      {!isLoading && !isError && (
        <Card className="divide-y divide-slate-100">
          {(flags ?? []).map((flag) => (
            <div key={flag.module} className="flex items-center justify-between gap-4 px-4 py-3.5">
              <div>
                <p className="text-sm font-semibold text-slate-800">{t(`featureModule.${flag.module}`)}</p>
                <p className="text-xs text-slate-500">{t(`featureModuleHint.${flag.module}`)}</p>
              </div>
              <Switch
                checked={flag.enabled}
                disabled={ALWAYS_ON.includes(flag.module) || updateFlag.isPending}
                onChange={(checked) => handleToggle(flag.module, checked)}
                label={t(`featureModule.${flag.module}`)}
              />
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}
