import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { ArrowRightLeft, Combine } from "lucide-react";

import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import { parseApiError } from "@/api/errors";
import { useTransferSession, useMergeSessions } from "@/features/orders/hooks";
import type { LocationOut } from "@/types/models";

type Mode = "transfer" | "merge";

/** One dialog for both moves, since they're the same underlying question
 * ("send this table's order somewhere else") with two different answers:
 * an empty table to relocate to, or an occupied one to combine with. Both
 * are rejected server-side once a bill exists for either session — see
 * order_service._reject_if_billed. */
export function TableMoveDialog({
  table,
  sessionId,
  allTables,
  sessionIdByLocation,
  onClose,
}: {
  table: LocationOut | null;
  sessionId: string | null;
  allTables: LocationOut[];
  sessionIdByLocation: Map<string, string>;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [mode, setMode] = useState<Mode>("transfer");
  const [targetId, setTargetId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const transfer = useTransferSession();
  const merge = useMergeSessions();
  const isPending = transfer.isPending || merge.isPending;

  const availableTables = allTables.filter((t2) => t2.id !== table?.id && t2.status === "AVAILABLE");
  const occupiedTables = allTables.filter(
    (t2) => t2.id !== table?.id && t2.status !== "AVAILABLE" && sessionIdByLocation.has(t2.id)
  );
  const options = mode === "transfer" ? availableTables : occupiedTables;

  const reset = () => {
    setMode("transfer");
    setTargetId("");
    setError(null);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleConfirm = () => {
    if (!table || !sessionId || !targetId) return;
    setError(null);
    if (mode === "transfer") {
      transfer.mutate(
        { sessionId, locationId: targetId },
        {
          onSuccess: () => {
            toast.success(t("tables.transferred", { name: table.name }));
            handleClose();
          },
          onError: (err) => setError(parseApiError(err).message),
        }
      );
    } else {
      const intoSessionId = sessionIdByLocation.get(targetId);
      if (!intoSessionId) return;
      merge.mutate(
        { sessionId, intoSessionId },
        {
          onSuccess: () => {
            toast.success(t("tables.merged", { name: table.name }));
            handleClose();
          },
          onError: (err) => setError(parseApiError(err).message),
        }
      );
    }
  };

  return (
    <Dialog open={Boolean(table)} onClose={handleClose} title={t("tables.moveTitle", { name: table?.name })} size="sm">
      <div className="space-y-4">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => {
              setMode("transfer");
              setTargetId("");
              setError(null);
            }}
            className={cn(
              "flex flex-1 flex-col items-center gap-1.5 rounded-lg border px-3 py-3 text-xs font-semibold transition-colors focus-ring",
              mode === "transfer" ? "border-brand-500 bg-brand-50 text-brand-700" : "border-stone-200 text-stone-600 hover:bg-stone-50"
            )}
          >
            <ArrowRightLeft size={16} />
            {t("tables.transferMode")}
          </button>
          <button
            type="button"
            onClick={() => {
              setMode("merge");
              setTargetId("");
              setError(null);
            }}
            className={cn(
              "flex flex-1 flex-col items-center gap-1.5 rounded-lg border px-3 py-3 text-xs font-semibold transition-colors focus-ring",
              mode === "merge" ? "border-brand-500 bg-brand-50 text-brand-700" : "border-stone-200 text-stone-600 hover:bg-stone-50"
            )}
          >
            <Combine size={16} />
            {t("tables.mergeMode")}
          </button>
        </div>

        <p className="text-xs text-stone-500">
          {mode === "transfer" ? t("tables.transferHint") : t("tables.mergeHint")}
        </p>

        {error && <p className="rounded-lg border border-danger-500/30 bg-danger-50 px-3 py-2 text-xs text-danger-700">{error}</p>}

        {options.length === 0 ? (
          <p className="rounded-lg bg-stone-50 px-3 py-2 text-sm text-stone-400">
            {mode === "transfer" ? t("tables.noAvailableTables") : t("tables.noOccupiedTables")}
          </p>
        ) : (
          <div className="grid grid-cols-3 gap-2">
            {options.map((opt) => (
              <button
                key={opt.id}
                type="button"
                onClick={() => setTargetId(opt.id)}
                className={cn(
                  "rounded-lg border px-2 py-2 text-sm font-semibold transition-colors focus-ring",
                  targetId === opt.id ? "border-brand-500 bg-brand-50 text-brand-700" : "border-stone-200 text-stone-700 hover:bg-stone-50"
                )}
              >
                {opt.name}
              </button>
            ))}
          </div>
        )}

        <Button className="w-full" size="lg" isLoading={isPending} disabled={!targetId} onClick={handleConfirm}>
          {mode === "transfer" ? t("tables.confirmTransfer") : t("tables.confirmMerge")}
        </Button>
      </div>
    </Dialog>
  );
}
