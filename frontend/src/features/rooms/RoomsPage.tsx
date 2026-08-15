import { useState } from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle, Pencil, Plus, QrCode, Trash2, Users } from "lucide-react";
import toast from "react-hot-toast";

import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { cn } from "@/lib/cn";
import { parseApiError } from "@/api/errors";
import { useDeleteRoom, useRooms } from "@/features/rooms/hooks";
import { RoomFormDialog } from "@/features/rooms/components/RoomFormDialog";
import type { LocationOut, LocationStatus } from "@/types/models";

const STATUS_CLASSES: Record<LocationStatus, string> = {
  AVAILABLE: "border-success-300 bg-success-50 text-success-700",
  OCCUPIED: "border-warning-300 bg-warning-50 text-warning-700",
  ORDERING: "border-warning-300 bg-warning-50 text-warning-700",
  KITCHEN: "border-brand-300 bg-brand-50 text-brand-700",
  READY: "border-brand-300 bg-brand-50 text-brand-700",
  SERVED: "border-brand-300 bg-brand-50 text-brand-700",
  BILL_PENDING: "border-danger-300 bg-danger-50 text-danger-700",
  PAID: "border-slate-300 bg-slate-100 text-slate-500",
  CLOSED: "border-slate-300 bg-slate-100 text-slate-500",
};

export function RoomsPage() {
  const { t } = useTranslation();
  const { data: rooms, isLoading, isError } = useRooms();
  const deleteRoom = useDeleteRoom();
  const [qrRoom, setQrRoom] = useState<LocationOut | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editingRoom, setEditingRoom] = useState<LocationOut | null>(null);

  const handleDelete = async (room: LocationOut) => {
    if (!window.confirm(t("rooms.confirmDelete", { name: room.name }))) return;
    try {
      await deleteRoom.mutateAsync(room.id);
      toast.success(t("rooms.roomDeleted"));
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  return (
    <div>
      <PageHeader
        title={t("nav.rooms")}
        subtitle={t("rooms.subtitle")}
        actions={
          <Button
            onClick={() => {
              setEditingRoom(null);
              setFormOpen(true);
            }}
          >
            <Plus size={16} />
            {t("rooms.addRoom")}
          </Button>
        }
      />

      {isLoading && (
        <div className="flex justify-center py-16">
          <Spinner className="text-brand-600" />
        </div>
      )}

      {isError && (
        <div className="flex flex-col items-center gap-2 py-16 text-danger-600">
          <AlertTriangle size={22} />
          <p className="text-sm font-medium">{t("rooms.loadError")}</p>
        </div>
      )}

      {!isLoading && !isError && rooms && rooms.length === 0 && (
        <p className="py-16 text-center text-sm text-slate-400">{t("rooms.noRooms")}</p>
      )}

      {!isLoading && !isError && rooms && rooms.length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {rooms.map((room) => (
            <Card
              key={room.id}
              className={cn("group relative flex flex-col items-center gap-1.5 border-2 p-4", STATUS_CLASSES[room.status])}
            >
              <span className="absolute right-1.5 top-1.5 hidden items-center gap-0.5 group-hover:flex">
                <button
                  type="button"
                  onClick={() => {
                    setEditingRoom(room);
                    setFormOpen(true);
                  }}
                  className="rounded p-1 hover:bg-white/70"
                  aria-label={t("rooms.editRoom")}
                >
                  <Pencil size={12} />
                </button>
                <button
                  type="button"
                  onClick={() => void handleDelete(room)}
                  className="rounded p-1 hover:bg-white/70"
                  aria-label={t("rooms.deleteRoom")}
                >
                  <Trash2 size={12} />
                </button>
              </span>
              <span className="text-base font-bold">{room.name}</span>
              {room.room_type && <span className="text-[10px] font-medium opacity-70">{room.room_type}</span>}
              <span className="text-[11px] font-semibold uppercase tracking-wide opacity-75">
                {t(`tableStatus.${room.status}`)}
              </span>
              {room.capacity != null && (
                <span className="mt-1 flex items-center gap-1 text-xs opacity-70">
                  <Users size={12} /> {room.capacity}
                </span>
              )}
              {room.qr_url && (
                <button
                  type="button"
                  onClick={() => setQrRoom(room)}
                  className="mt-1 flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-semibold opacity-80 hover:bg-white/60 hover:opacity-100 focus-ring"
                >
                  <QrCode size={12} /> {t("tables.qrLink")}
                </button>
              )}
            </Card>
          ))}
        </div>
      )}

      <Dialog open={Boolean(qrRoom)} onClose={() => setQrRoom(null)} title={t("tables.qrDialogTitle", { name: qrRoom?.name })} size="sm">
        {qrRoom?.qr_url && (
          <div className="space-y-3">
            <p className="text-sm text-slate-500">{t("rooms.qrDialogHint")}</p>
            <p className="break-all rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
              {qrRoom.qr_url}
            </p>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                className="flex-1"
                onClick={() => {
                  void navigator.clipboard.writeText(qrRoom.qr_url as string);
                  toast.success(t("tables.qrLinkCopied"));
                }}
              >
                {t("tables.copyLink")}
              </Button>
              <a href={qrRoom.qr_url} target="_blank" rel="noreferrer" className="flex-1">
                <Button className="w-full">{t("tables.openLink")}</Button>
              </a>
            </div>
          </div>
        )}
      </Dialog>

      <RoomFormDialog open={formOpen} room={editingRoom} onClose={() => setFormOpen(false)} />
    </div>
  );
}
