import { useTranslation } from "react-i18next";
import { AlertTriangle, Check, X } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { useFeatureFlags } from "@/features/settings/hooks";

/** Read-only. What a business is entitled to is set by WhyNotGrace, not
 * the business itself — see backend/app/api/feature_flags.py's docstring
 * for why the write path was removed. */
export function FeatureFlagsPage() {
  const { t } = useTranslation();
  const { data: flags, isLoading, isError } = useFeatureFlags();

  return (
    <div>
      <PageHeader title={t("nav.featureFlags")} subtitle={t("featureFlags.subtitle")} />

      <p className="mb-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-xs text-slate-600">
        {t("featureFlags.readOnlyNotice")}
      </p>

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
              {flag.enabled ? (
                <span className="flex items-center gap-1.5 rounded-full bg-success-50 px-2.5 py-1 text-xs font-semibold text-success-700">
                  <Check size={13} />
                  {t("featureFlags.on")}
                </span>
              ) : (
                <span className="flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-500">
                  <X size={13} />
                  {t("featureFlags.off")}
                </span>
              )}
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}
