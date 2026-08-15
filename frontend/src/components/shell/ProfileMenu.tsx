import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ChevronDown, LogOut, UserRound } from "lucide-react";
import { cn } from "@/lib/cn";
import { useClickOutside } from "@/hooks/useClickOutside";
import { useAuthStore } from "@/stores/authStore";
import { useLogout } from "@/features/auth/hooks";

function initials(firstName: string, lastName: string) {
  return `${firstName[0] ?? ""}${lastName[0] ?? ""}`.toUpperCase();
}

export function ProfileMenu() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const logout = useLogout();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useClickOutside(ref, () => setOpen(false), open);

  if (!user) return null;

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-lg py-1 pl-1 pr-2 hover:bg-slate-100 focus-ring"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">
          {initials(user.first_name, user.last_name)}
        </div>
        <div className="hidden text-left leading-tight sm:block">
          <p className="text-sm font-semibold text-slate-800">
            {user.first_name} {user.last_name}
          </p>
          <p className="text-xs text-slate-500">{t(`roles.${user.role}`)}</p>
        </div>
        <ChevronDown size={16} className="text-slate-400" />
      </button>

      {open && (
        <div
          role="menu"
          className={cn(
            "absolute right-0 z-50 mt-2 w-56 overflow-hidden rounded-lg border border-slate-200 bg-white py-1 shadow-popover"
          )}
        >
          <button
            role="menuitem"
            type="button"
            onClick={() => {
              setOpen(false);
              navigate("/profile");
            }}
            className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
          >
            <UserRound size={16} />
            {t("shell.profile")}
          </button>
          <div className="my-1 border-t border-slate-100" />
          <button
            role="menuitem"
            type="button"
            onClick={() => {
              setOpen(false);
              logout.mutate();
            }}
            className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm text-danger-600 hover:bg-danger-50"
          >
            <LogOut size={16} />
            {t("shell.logout")}
          </button>
        </div>
      )}
    </div>
  );
}
