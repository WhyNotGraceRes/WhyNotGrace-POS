import type { ComponentType } from "react";
import { Card } from "@/components/ui/Card";
import { cn } from "@/lib/cn";

interface StatCardProps {
  label: string;
  value: string;
  icon: ComponentType<{ size?: number; className?: string }>;
  hint?: string;
  tone?: "default" | "warning" | "success";
}

const toneClasses: Record<NonNullable<StatCardProps["tone"]>, string> = {
  default: "bg-brand-50 text-brand-700",
  warning: "bg-warning-50 text-warning-600",
  success: "bg-success-50 text-success-600",
};

export function StatCard({ label, value, icon: Icon, hint, tone = "default" }: StatCardProps) {
  return (
    <Card className="flex items-start gap-3 p-4">
      <div className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-xl", toneClasses[tone])}>
        <Icon size={18} />
      </div>
      <div className="min-w-0">
        <p className="truncate text-xs font-medium text-stone-500">{label}</p>
        <p className="mt-0.5 text-xl font-bold tracking-tight tabular-nums text-stone-900">{value}</p>
        {hint && <p className="mt-0.5 truncate text-xs text-stone-400">{hint}</p>}
      </div>
    </Card>
  );
}

export function StatCardSkeleton() {
  return (
    <Card className="flex items-start gap-3 p-4">
      <div className="h-9 w-9 shrink-0 animate-pulse rounded-lg bg-stone-200" />
      <div className="min-w-0 flex-1 space-y-2">
        <div className="h-3 w-20 animate-pulse rounded bg-stone-200" />
        <div className="h-6 w-14 animate-pulse rounded bg-stone-200" />
      </div>
    </Card>
  );
}
