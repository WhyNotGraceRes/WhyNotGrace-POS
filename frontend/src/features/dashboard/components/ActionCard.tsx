import type { ComponentType } from "react";
import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { cn } from "@/lib/cn";

interface ActionCardProps {
  label: string;
  count: number;
  icon: ComponentType<{ size?: number; className?: string }>;
  to: string;
  /** When true, a non-zero count is good news (e.g. "ready to serve" still
   * needs someone to act on it, but isn't a problem the way a stuck queue
   * is) — shown in success rather than warning color. */
  positiveWhenNonZero?: boolean;
  /** Small line under the count — e.g. "Oldest: 18m" or a status
   * breakdown. Context for the number, not a second thing to read first. */
  hint?: string;
}

/** The "needs attention right now" strip — every card here is a queue with
 * a real place to go work through it, not a number to just read. Matches
 * the pattern competitor dashboards (Petpooja, Toast) use: the dashboard
 * is a launch pad into work, not a dead-end report. Idle (count 0) cards
 * stay visually quiet on purpose, so a real queue is the only thing that
 * draws the eye.
 */
export function ActionCard({ label, count, icon: Icon, to, positiveWhenNonZero, hint }: ActionCardProps) {
  const isIdle = count === 0;
  const tone = isIdle ? "idle" : positiveWhenNonZero ? "success" : "warning";

  const toneClasses = {
    idle: { icon: "bg-stone-100 text-stone-400", ring: "" },
    success: { icon: "bg-success-50 text-success-600", ring: "ring-1 ring-success-200" },
    warning: { icon: "bg-warning-50 text-warning-600", ring: "ring-1 ring-warning-200" },
  }[tone];

  return (
    <Link to={to} className="block">
      <Card className={cn("interactive-card flex items-center gap-3 p-4", toneClasses.ring)}>
        <div className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-xl", toneClasses.icon)}>
          <Icon size={19} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-medium text-stone-500">{label}</p>
          <p className="mt-0.5 text-2xl font-bold tracking-tight tabular-nums text-stone-900">{count}</p>
          {hint && <p className="mt-0.5 truncate text-xs text-stone-400">{hint}</p>}
        </div>
        <ChevronRight size={16} className="shrink-0 text-stone-300" />
      </Card>
    </Link>
  );
}

export function ActionCardSkeleton() {
  return (
    <Card className="flex items-center gap-3 p-4">
      <div className="h-10 w-10 shrink-0 animate-pulse rounded-lg bg-stone-200" />
      <div className="min-w-0 flex-1 space-y-2">
        <div className="h-3 w-16 animate-pulse rounded bg-stone-200" />
        <div className="h-6 w-8 animate-pulse rounded bg-stone-200" />
      </div>
    </Card>
  );
}
