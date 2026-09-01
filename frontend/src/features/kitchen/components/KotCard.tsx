import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { Clock, Printer, X } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { minutesSince } from "@/lib/format";
import { cn } from "@/lib/cn";
import { printKotForAllStations } from "@/lib/printReceipt";
import type { KOTOut, KOTStatus } from "@/types/models";

const NEXT_STATUS: Partial<Record<KOTStatus, KOTStatus>> = {
  NEW: "ACCEPTED",
  ACCEPTED: "PREPARING",
  PREPARING: "READY",
};

const NEXT_LABEL_KEY: Partial<Record<KOTStatus, string>> = {
  NEW: "kitchen.accept",
  ACCEPTED: "kitchen.startPreparing",
  PREPARING: "kitchen.markReady",
};

const AGE_TONE = (minutes: number) =>
  minutes >= 15 ? "border-danger-300 bg-danger-50" : minutes >= 8 ? "border-warning-300 bg-warning-50" : "border-stone-200 bg-white";

export function KotCard({
  kot,
  onAdvance,
  onCancel,
  isUpdating,
}: {
  kot: KOTOut;
  onAdvance: (kot: KOTOut, next: KOTStatus) => void;
  onCancel: (kot: KOTOut) => void;
  isUpdating: boolean;
}) {
  const { t } = useTranslation();
  const age = minutesSince(kot.created_at);
  const next = NEXT_STATUS[kot.status];
  const [isPrinting, setIsPrinting] = useState(false);

  const handlePrint = async () => {
    setIsPrinting(true);
    try {
      const stationCount = await printKotForAllStations(kot.id);
      if (stationCount > 1) toast.success(t("kitchen.printedStationTickets", { count: stationCount }));
    } catch {
      toast.error(t("kitchen.printFailed"));
    } finally {
      setIsPrinting(false);
    }
  };

  return (
    <Card className={cn("flex flex-col gap-3 border-2 p-4", AGE_TONE(age))}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-bold text-stone-900">{kot.kot_number}</p>
          <p className="flex items-center gap-1 text-xs text-stone-500">
            <Clock size={12} />
            {t("kitchen.minutesAgo", { count: age })}
          </p>
        </div>
        <span className="rounded-full bg-stone-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-stone-500">
          {t(`kotStatus.${kot.status}`)}
        </span>
      </div>

      <ul className="space-y-1.5">
        {kot.items.map((item) => (
          <li key={item.id} className="text-sm">
            <span className="font-semibold text-stone-800">{item.quantity} × </span>
            <span className="text-stone-700">{item.item_name_snapshot}</span>
            {item.options_summary && <p className="pl-5 text-xs text-stone-500">{item.options_summary}</p>}
          </li>
        ))}
      </ul>

      {kot.special_instructions && (
        <p className="rounded-md bg-accent-50 px-2 py-1.5 text-xs italic text-accent-800">
          "{kot.special_instructions}"
        </p>
      )}

      <div className="mt-auto flex items-center gap-2 pt-1">
        {next && (
          <Button className="flex-1" isLoading={isUpdating} onClick={() => onAdvance(kot, next)}>
            {t(NEXT_LABEL_KEY[kot.status] as string)}
          </Button>
        )}
        <Button
          variant="ghost"
          size="md"
          isLoading={isPrinting}
          disabled={isUpdating}
          onClick={() => void handlePrint()}
          aria-label={t("kitchen.printKot")}
        >
          <Printer size={16} />
        </Button>
        <Button
          variant="ghost"
          size="md"
          disabled={isUpdating}
          onClick={() => onCancel(kot)}
          aria-label={t("kitchen.cancelKot")}
        >
          <X size={16} />
        </Button>
      </div>
    </Card>
  );
}
