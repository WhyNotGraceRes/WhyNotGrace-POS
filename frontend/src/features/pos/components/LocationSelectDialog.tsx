import { useTranslation } from "react-i18next";
import { Dialog } from "@/components/ui/Dialog";
import { Spinner } from "@/components/ui/Spinner";
import { cn } from "@/lib/cn";
import { useTables } from "@/features/tables/hooks";
import { useRooms } from "@/features/rooms/hooks";
import type { LocationStatus } from "@/types/models";

const STATUS_CLASSES: Record<LocationStatus, string> = {
  AVAILABLE: "border-success-500/40 bg-success-50 text-success-700",
  OCCUPIED: "border-warning-500/40 bg-warning-50 text-warning-700",
  ORDERING: "border-warning-500/40 bg-warning-50 text-warning-700",
  KITCHEN: "border-brand-500/40 bg-brand-50 text-brand-700",
  READY: "border-brand-500/40 bg-brand-50 text-brand-700",
  SERVED: "border-brand-500/40 bg-brand-50 text-brand-700",
  BILL_PENDING: "border-danger-500/40 bg-danger-50 text-danger-700",
  PAID: "border-stone-300 bg-stone-100 text-stone-500",
  CLOSED: "border-stone-300 bg-stone-100 text-stone-500",
};

/** Shared by dine-in table selection and hotel room-service room
 * selection — both are just Locations targeted through the same order
 * engine (backend/app/services/order_service.py), never two separate
 * systems. */
export function LocationSelectDialog({
  open,
  onClose,
  onSelect,
  mode,
}: {
  open: boolean;
  onClose: () => void;
  onSelect: (id: string, name: string) => void;
  mode: "TABLE" | "ROOM";
}) {
  const { t } = useTranslation();
  const tablesQuery = useTables();
  const roomsQuery = useRooms({ enabled: mode === "ROOM" });
  const { data: locations, isLoading, isError } = mode === "TABLE" ? tablesQuery : roomsQuery;

  const emptyKey = mode === "TABLE" ? "pos.noTables" : "rooms.noRooms";
  const errorKey = mode === "TABLE" ? "pos.tablesLoadError" : "rooms.loadError";

  return (
    <Dialog open={open} onClose={onClose} title={mode === "TABLE" ? t("pos.selectTable") : t("pos.selectRoom")} size="lg">
      {isLoading && (
        <div className="flex justify-center py-10">
          <Spinner className="text-brand-600" />
        </div>
      )}

      {isError && <p className="py-6 text-center text-sm text-danger-600">{t(errorKey)}</p>}

      {locations && locations.length === 0 && <p className="py-6 text-center text-sm text-stone-400">{t(emptyKey)}</p>}

      {locations && locations.length > 0 && (
        <div className="grid grid-cols-3 gap-2.5 sm:grid-cols-4">
          {locations.map((location) => (
            <button
              key={location.id}
              type="button"
              onClick={() => {
                onSelect(location.id, location.name);
                onClose();
              }}
              className={cn(
                "flex flex-col items-center gap-1 rounded-lg border-2 px-3 py-3 text-sm font-semibold transition-colors focus-ring",
                STATUS_CLASSES[location.status]
              )}
            >
              <span>{location.name}</span>
              <span className="text-[10px] font-medium uppercase tracking-wide opacity-70">
                {t(`tableStatus.${location.status}`)}
              </span>
            </button>
          ))}
        </div>
      )}
    </Dialog>
  );
}
