import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { RotateCcw } from "lucide-react";
import { elapsedSince } from "@/lib/format";

/** Ticks every 15s purely to force a re-render, so a "12s ago" label
 * actually counts up on screen instead of only updating whenever the page
 * happens to re-render for some other reason (e.g. the next refetch). */
function useClockTick(intervalMs: number) {
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((n) => n + 1), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
}

/** The "how current is this" + manual-refresh control shown in a page
 * header's actions slot. One implementation shared by every live-data
 * page (owner dashboard, counter home) so a cashier gets the same
 * confidence about freshness an owner does — same label, same spinner,
 * same tap target, everywhere it appears. */
export function FreshnessIndicator({
  dataUpdatedAt,
  isFetching,
  onRefresh,
}: {
  dataUpdatedAt: number;
  isFetching: boolean;
  onRefresh: () => void;
}) {
  const { t } = useTranslation();
  useClockTick(15_000);

  const elapsed = elapsedSince(dataUpdatedAt);
  const updatedLabel =
    elapsed.unit === "now"
      ? t("dashboard.updatedJustNow")
      : elapsed.unit === "seconds"
        ? t("dashboard.updatedSecondsAgo", { count: elapsed.count })
        : elapsed.unit === "minutes"
          ? t("dashboard.updatedMinutesAgo", { count: elapsed.count })
          : t("dashboard.updatedHoursAgo", { count: elapsed.count });

  return (
    <div className="flex items-center gap-2 text-xs text-slate-400">
      <span>{updatedLabel}</span>
      <button
        type="button"
        onClick={onRefresh}
        disabled={isFetching}
        aria-label={t("dashboard.refresh")}
        title={t("dashboard.refresh")}
        className="rounded-full p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 disabled:opacity-50"
      >
        <RotateCcw size={14} className={isFetching ? "animate-spin" : ""} />
      </button>
    </div>
  );
}
