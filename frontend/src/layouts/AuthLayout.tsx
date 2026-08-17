import { Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";

export function AuthLayout() {
  const { t } = useTranslation();

  return (
    <div className="flex min-h-screen flex-col bg-stone-50">
      <header className="flex items-center justify-between px-6 py-5 sm:px-10">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-sm font-bold text-white">
            W
          </div>
          <span className="text-lg font-bold tracking-tight text-stone-900">{t("common.appName")}</span>
        </div>
        <LanguageSwitcher />
      </header>

      <main className="flex flex-1 items-center justify-center px-4 pb-16">
        <div className="w-full max-w-md">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
