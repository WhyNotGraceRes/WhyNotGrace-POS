import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Bell } from "lucide-react";
import { useClickOutside } from "@/hooks/useClickOutside";

/**
 * Visual placeholder only. The backend has no notifications API yet, so
 * this deliberately shows no badge/count/fake items — just an honest
 * "nothing to show" state. Wire this up once a real endpoint exists.
 */
export function NotificationsButton() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useClickOutside(ref, () => setOpen(false), open);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="rounded-lg p-2 text-stone-500 hover:bg-stone-100 hover:text-stone-700 focus-ring"
        aria-label={t("shell.notifications")}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <Bell size={18} />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-2 w-64 rounded-lg border border-stone-200 bg-white p-4 shadow-popover"
        >
          <p className="text-sm font-semibold text-stone-800">{t("shell.notifications")}</p>
          <p className="mt-1 text-sm text-stone-500">{t("shell.noNotifications")}</p>
        </div>
      )}
    </div>
  );
}
