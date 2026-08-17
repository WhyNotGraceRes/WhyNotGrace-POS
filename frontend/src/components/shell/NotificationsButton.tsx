import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Bell, ShoppingBag, AlertTriangle } from "lucide-react";
import { useClickOutside } from "@/hooks/useClickOutside";
import { minutesSince } from "@/lib/format";
import { cn } from "@/lib/cn";
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
} from "@/features/notifications/hooks";
import type { NotificationOut } from "@/types/models";

const RESOURCE_ROUTE: Record<string, string> = {
  order: "/orders",
  kot: "/kitchen",
};

const TYPE_ICON: Record<string, typeof Bell> = {
  NEW_CUSTOMER_ORDER: ShoppingBag,
  STUCK_KOT: AlertTriangle,
};

export function NotificationsButton() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useClickOutside(ref, () => setOpen(false), open);

  const { data } = useNotifications();
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();

  const notifications = data?.notifications ?? [];
  const unreadCount = data?.unread_count ?? 0;

  const handleClick = (n: NotificationOut) => {
    // The "tickets are aging" notice isn't a stored row (see
    // notification_service._stuck_kot_notice) — there's nothing to mark
    // read, it just stops appearing once no ticket is over the age
    // threshold anymore.
    if (n.type !== "STUCK_KOT" && !n.is_read) {
      markRead.mutate(n.id);
    }
    setOpen(false);
    const route = n.resource_type ? RESOURCE_ROUTE[n.resource_type] : undefined;
    if (route) navigate(route);
  };

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="relative rounded-lg p-2 text-stone-500 hover:bg-stone-100 hover:text-stone-700 focus-ring"
        aria-label={t("shell.notifications")}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger-500 px-1 text-[10px] font-bold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-2 w-80 rounded-lg border border-stone-200 bg-white p-2 shadow-popover"
        >
          <div className="flex items-center justify-between px-2 py-1.5">
            <p className="text-sm font-semibold text-stone-800">{t("shell.notifications")}</p>
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={() => markAllRead.mutate()}
                className="text-xs font-semibold text-brand-700 hover:underline focus-ring"
              >
                {t("shell.markAllRead")}
              </button>
            )}
          </div>

          {notifications.length === 0 && (
            <p className="px-2 py-3 text-sm text-stone-500">{t("shell.noNotifications")}</p>
          )}

          <ul className="max-h-80 space-y-0.5 overflow-y-auto">
            {notifications.map((n) => {
              const Icon = TYPE_ICON[n.type] ?? Bell;
              const age = minutesSince(n.created_at);
              return (
                <li key={n.id}>
                  <button
                    type="button"
                    onClick={() => handleClick(n)}
                    className={cn(
                      "flex w-full items-start gap-2.5 rounded-lg px-2 py-2 text-left transition-colors hover:bg-stone-50 focus-ring",
                      !n.is_read && "bg-brand-50/40"
                    )}
                  >
                    <Icon size={15} className={cn("mt-0.5 shrink-0", !n.is_read ? "text-brand-600" : "text-stone-400")} />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-stone-800">{n.title}</span>
                      {n.body && <span className="block truncate text-xs text-stone-500">{n.body}</span>}
                      <span className="mt-0.5 block text-[11px] text-stone-400">{t("kitchen.minutesAgo", { count: age })}</span>
                    </span>
                    {!n.is_read && <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
