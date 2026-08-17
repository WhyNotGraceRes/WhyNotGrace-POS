import type { ReactNode } from "react";

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-7 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-stone-900 sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1.5 text-sm text-stone-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
