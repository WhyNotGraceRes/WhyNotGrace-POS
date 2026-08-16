import { useTranslation } from "react-i18next";
import { UtensilsCrossed, Package, Truck } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { formatNumber } from "@/lib/format";

interface Channel {
  key: string;
  labelKey: string;
  count: number;
  icon: typeof UtensilsCrossed;
}

/** One grouped comparison instead of separate same-weight stat cards per
 * channel — the flat grid this replaced showed pickup/delivery/website as
 * three unrelated cards scattered among unrelated metrics, which hides the
 * thing an owner actually wants to see at a glance: where today's orders
 * are coming from, compared to each other. Dine-in is derived (today's
 * total minus every other channel) rather than tracked directly, since
 * the backend's /dashboard response has no separate dine-in counter.
 *
 * Deliberately excludes "website orders" as its own bar: the backend
 * defines website_orders_today as pickup_today + delivery_today (see
 * dashboard_service.py) — it's not a fourth peer channel, every website
 * order already IS a pickup or a delivery order. Showing it as a fourth
 * bar double-subtracted pickup+delivery from dine-in and silently zeroed
 * dine-in out in testing whenever ONLINE_WEBSITE was also enabled. */
export function ChannelBreakdown({
  ordersToday,
  pickupToday,
  deliveryToday,
  pickupEnabled,
  deliveryEnabled,
}: {
  ordersToday: number;
  pickupToday: number;
  deliveryToday: number;
  pickupEnabled: boolean;
  deliveryEnabled: boolean;
}) {
  const { t } = useTranslation();

  // If no alternate channel is enabled, every order is dine-in and this
  // card would say nothing a single "orders today" number doesn't already.
  if (!pickupEnabled && !deliveryEnabled) return null;

  const dineIn = Math.max(0, ordersToday - pickupToday - deliveryToday);

  const channels: Channel[] = [{ key: "dine_in", labelKey: "dashboard.channelDineIn", count: dineIn, icon: UtensilsCrossed }];
  if (pickupEnabled) channels.push({ key: "pickup", labelKey: "dashboard.channelPickup", count: pickupToday, icon: Package });
  if (deliveryEnabled) channels.push({ key: "delivery", labelKey: "dashboard.channelDelivery", count: deliveryToday, icon: Truck });

  const max = Math.max(1, ...channels.map((c) => c.count));

  return (
    <Card className="p-5">
      <h2 className="text-sm font-bold text-slate-900">{t("dashboard.channelBreakdown")}</h2>
      <p className="text-xs text-slate-500">{t("dashboard.channelBreakdownSubtitle")}</p>

      <ul className="mt-4 space-y-3">
        {channels.map((channel) => (
          <li key={channel.key} className="flex items-center gap-3">
            <channel.icon size={16} className="shrink-0 text-slate-400" />
            <span className="w-16 shrink-0 text-xs font-medium text-slate-600">{t(channel.labelKey)}</span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-brand-500"
                style={{ width: `${(channel.count / max) * 100}%` }}
              />
            </div>
            <span className="w-8 shrink-0 text-right text-sm font-semibold tabular-nums text-slate-800">
              {formatNumber(channel.count)}
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
