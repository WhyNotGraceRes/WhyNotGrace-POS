import { useTranslation } from "react-i18next";
import { Menu } from "lucide-react";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { NotificationsButton } from "@/components/shell/NotificationsButton";
import { ProfileMenu } from "@/components/shell/ProfileMenu";

export function Header({ onMenuClick }: { onMenuClick: () => void }) {
  const { t } = useTranslation();

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-6">
      <button
        type="button"
        onClick={onMenuClick}
        className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-700 focus-ring lg:hidden"
        aria-label={t("shell.openMenu")}
      >
        <Menu size={20} />
      </button>

      <div className="hidden lg:block" />

      <div className="flex items-center gap-1.5 sm:gap-2">
        <LanguageSwitcher />
        <NotificationsButton />
        <div className="mx-1 h-6 w-px bg-slate-200" />
        <ProfileMenu />
      </div>
    </header>
  );
}
