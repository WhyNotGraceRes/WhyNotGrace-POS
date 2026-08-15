import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Card } from "@/components/ui/Card";
import { useAuthStore } from "@/stores/authStore";
import { useBusiness } from "@/features/business/hooks";
import { useFeatureFlags } from "@/features/settings/hooks";
import { getVisibleNavItems } from "@/config/navigation";
import type { FeatureModule } from "@/types/models";

/**
 * Landing page for roles the backend does not grant dashboard access to
 * (CASH_COUNTER, SERVICE_COUNTER, KITCHEN, DELIVERY — see
 * backend/app/api/dashboard.py: GET /dashboard is OWNER/MANAGER only).
 * Deliberately shows no statistics: there is no backend endpoint scoped
 * to give these roles a safe, permitted summary, and calling /dashboard
 * for them would just be a guaranteed 403. Quick links to what they can
 * actually do stand in for it instead.
 */
export function RoleHomePage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const { data: business } = useBusiness();
  const { data: flags } = useFeatureFlags();

  const isFeatureEnabled = (module: FeatureModule) =>
    flags?.find((f) => f.module === module)?.enabled ?? false;

  const items = user ? getVisibleNavItems(user.role, isFeatureEnabled).filter((i) => i.path !== "/") : [];

  if (!user) return null;

  return (
    <div>
      <h1 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
        {t("roleHome.welcome", { name: user.first_name })}
      </h1>
      <p className="mt-1 text-sm text-slate-500">
        {t("roleHome.subtitle", { role: t(`roles.${user.role}`), business: business?.name ?? "…" })}
      </p>

      {items.length > 0 && (
        <div className="mt-6">
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
            {t("roleHome.quickLinks")}
          </h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {items.map((item) => (
              <Link key={item.path} to={item.path}>
                <Card className="flex flex-col items-start gap-3 p-4 transition-shadow hover:shadow-popover">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
                    <item.icon size={18} />
                  </div>
                  <span className="text-sm font-semibold text-slate-800">{t(item.labelKey)}</span>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
