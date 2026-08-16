import type { ComponentType } from "react";
import { Card } from "@/components/ui/Card";

interface HeroStatCardProps {
  label: string;
  value: string;
  icon: ComponentType<{ size?: number; className?: string }>;
  hint?: string;
}

/** The 3-5 numbers that matter most, shown larger than everything else on
 * the page — the top tier of the F-pattern scan a counter/owner does on
 * login. Deliberately not clickable: these are headline totals, not
 * queues to work through (see ActionCard for those). */
export function HeroStatCard({ label, value, icon: Icon, hint }: HeroStatCardProps) {
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
        <p className="text-sm font-medium leading-snug text-slate-500">{label}</p>
        <p className="mt-0.5 truncate text-2xl font-bold tabular-nums text-slate-900">{value}</p>
        {hint && <p className="mt-0.5 truncate text-xs text-slate-400">{hint}</p>}
      </div>
    </Card>
  );
}

export function HeroStatCardSkeleton() {
  return (
    <Card className="flex items-center gap-4 p-5">
      <div className="h-12 w-12 shrink-0 animate-pulse rounded-xl bg-slate-200" />
      <div className="min-w-0 flex-1 space-y-2">
        <div className="h-3.5 w-24 animate-pulse rounded bg-slate-200" />
        <div className="h-7 w-20 animate-pulse rounded bg-slate-200" />
      </div>
    </Card>
  );
}
