import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";
import { useAuthStore } from "@/stores/authStore";
import { useBusiness } from "@/features/business/hooks";
import { useFeatureFlags } from "@/features/settings/hooks";
import { getVisibleNavItems } from "@/config/navigation";
import type { FeatureModule } from "@/types/models";

interface SidebarProps {
  mobileOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ mobileOpen, onClose }: SidebarProps) {
  const { t } = useTranslation();
  const role = useAuthStore((s) => s.user?.role);
  const { data: business } = useBusiness();
  const { data: flags } = useFeatureFlags();

  const isFeatureEnabled = (module: FeatureModule) =>
    flags?.find((f) => f.module === module)?.enabled ?? false;

  const items = getVisibleNavItems(role, isFeatureEnabled);

  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-stone-900/40 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-stone-200 bg-white transition-transform duration-200 ease-out",
          "lg:static lg:z-auto lg:transtone-x-0",
          mobileOpen ? "transtone-x-0" : "-transtone-x-full"
        )}
      >
        <div className="flex h-16 shrink-0 items-center justify-between border-b border-stone-200 px-4">
          <div className="flex min-w-0 items-center gap-2">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-600 text-sm font-bold text-white">
              W
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-bold leading-tight text-stone-900">
                {business?.name ?? t("common.appName")}
              </p>
              {business && (
                <p className="truncate text-xs leading-tight text-stone-400">
                  {t(`auth.register.businessTypes.${business.business_type}`)}
                </p>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-stone-400 hover:bg-stone-100 hover:text-stone-600 lg:hidden focus-ring"
            aria-label={t("shell.closeMenu")}
          >
            <X size={18} />
          </button>
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-4">
          {items.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              onClick={onClose}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-brand-50 text-brand-700"
                    : "text-stone-600 hover:bg-stone-100 hover:text-stone-900"
                )
              }
            >
              <item.icon size={18} className="shrink-0" />
              <span className="truncate">{t(item.labelKey)}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  );
}
