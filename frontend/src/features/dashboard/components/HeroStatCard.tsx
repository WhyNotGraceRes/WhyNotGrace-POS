import type { ComponentType } from "react";
import { TrendingUp, TrendingDown } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { cn } from "@/lib/cn";

interface HeroStatCardProps {
  label: string;
  value: string;
  icon: ComponentType<{ size?: number; className?: string }>;
  hint?: string;
  /** "vs yesterday, same time" — see lib/format.ts's computeTrend. Omitted
   * entirely when there's nothing meaningful to compare against yet. */
  trend?: { direction: "up" | "down" | "flat"; percent: number | null; label: string };
}

/** The 3-5 numbers that matter most, shown larger than everything else on
 * the page — the top tier of the F-pattern scan a counter/owner does on
 * login. Deliberately not clickable: these are headline totals, not
 * queues to work through (see ActionCard for those). */
export function HeroStatCard({ label, value, icon: Icon, hint, trend }: HeroStatCardProps) {
  return (
    <Card className="flex items-center gap-4 p-5">
      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
        <Icon size={22} />
      </div>
      <div className="min-w-0">
        {/* Wraps rather than truncates — "Average order value" is longer
            than "Sales today"/"Orders today" and there's vertical room in
            this card; an ellipsis here would hide the label entirely
            rather than just clipping a character or two. */}
        <p className="text-sm font-medium leading-snug text-stone-500">{label}</p>
        <p className="mt-0.5 truncate text-3xl font-bold tracking-tight tabular-nums text-stone-900">{value}</p>
        {trend && (
          <p
            className={cn(
              "mt-0.5 flex items-center gap-1 truncate text-xs font-semibold",
              trend.direction === "up" ? "text-success-600" : trend.direction === "down" ? "text-danger-600" : "text-stone-400"
            )}
          >
            {trend.direction === "up" && <TrendingUp size={12} />}
            {trend.direction === "down" && <TrendingDown size={12} />}
            {trend.label}
          </p>
        )}
        {!trend && hint && <p className="mt-0.5 truncate text-xs text-stone-400">{hint}</p>}
      </div>
    </Card>
  );
}

export function HeroStatCardSkeleton() {
  return (
    <Card className="flex items-center gap-4 p-5">
      <div className="h-12 w-12 shrink-0 animate-pulse rounded-xl bg-stone-200" />
      <div className="min-w-0 flex-1 space-y-2">
        <div className="h-3.5 w-24 animate-pulse rounded bg-stone-200" />
        <div className="h-7 w-20 animate-pulse rounded bg-stone-200" />
      </div>
    </Card>
  );
}
