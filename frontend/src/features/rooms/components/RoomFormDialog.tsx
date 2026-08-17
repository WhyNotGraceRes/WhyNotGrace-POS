import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";

import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Switch } from "@/components/ui/Switch";
import { parseApiError } from "@/api/errors";
import { useCreateRoom, useUpdateRoom } from "@/features/rooms/hooks";
import type { LocationOut } from "@/types/models";

export function RoomFormDialog({
  open,
  room,
  onClose,
}: {
  open: boolean;
  room: LocationOut | null;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const createRoom = useCreateRoom();
  const updateRoom = useUpdateRoom();
  const isEdit = Boolean(room);

  const [name, setName] = useState(room?.name ?? "");
  const [capacity, setCapacity] = useState(room?.capacity != null ? String(room.capacity) : "");
  const [floor, setFloor] = useState(room?.floor ?? "");
  const [roomType, setRoomType] = useState(room?.room_type ?? "");
  const [isActive, setIsActive] = useState(room?.is_active ?? true);
  const [error, setError] = useState<string | null>(null);

  const [openId, setOpenId] = useState<string | null>(room?.id ?? null);
  if (open && (room?.id ?? null) !== openId) {
    setOpenId(room?.id ?? null);
    setName(room?.name ?? "");
    setCapacity(room?.capacity != null ? String(room.capacity) : "");
    setFloor(room?.floor ?? "");
    setRoomType(room?.room_type ?? "");
    setIsActive(room?.is_active ?? true);
    setError(null);
  }

  const isPending = createRoom.isPending || updateRoom.isPending;

  const handleSubmit = async () => {
    setError(null);
    if (!name.trim()) {
      setError(t("rooms.nameRequired"));
      return;
    }
    try {
      if (isEdit && room) {
        await updateRoom.mutateAsync({
          roomId: room.id,
          payload: {
            name: name.trim(),
            capacity: capacity ? Number(capacity) : null,
            floor: floor.trim() || null,
            room_type: roomType.trim() || null,
            is_active: isActive,
          },
        });
        toast.success(t("rooms.roomUpdated"));
      } else {
        await createRoom.mutateAsync({
          name: name.trim(),
          capacity: capacity ? Number(capacity) : undefined,
          floor: floor.trim() || undefined,
          room_type: roomType.trim() || undefined,
        });
        toast.success(t("rooms.roomCreated"));
      }
      onClose();
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title={isEdit ? t("rooms.editRoom") : t("rooms.addRoom")} size="sm">
      <div className="space-y-3">
        {error && <p className="text-xs text-danger-600">{error}</p>}
        <div>
          <Label htmlFor="room-name">{t("rooms.roomNumber")}</Label>
          <Input id="room-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="101" />
        </div>
        <div>
          <Label htmlFor="room-type">{t("rooms.roomType")}</Label>
          <Input id="room-type" value={roomType} onChange={(e) => setRoomType(e.target.value)} placeholder={t("rooms.roomTypePlaceholder")} />
        </div>
        <div>
          <Label htmlFor="room-capacity">{t("tables.capacity")}</Label>
          <Input id="room-capacity" type="number" min={1} value={capacity} onChange={(e) => setCapacity(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="room-floor">{t("tables.floor")}</Label>
          <Input id="room-floor" value={floor} onChange={(e) => setFloor(e.target.value)} />
        </div>
        {isEdit && (
          <label className="flex items-center gap-2 text-sm text-stone-700">
            <Switch checked={isActive} onChange={setIsActive} label={t("menuAdmin.isActive")} />
            {t("menuAdmin.isActive")}
          </label>
        )}
        <Button className="w-full" isLoading={isPending} onClick={() => void handleSubmit()}>
          {isEdit ? t("common.save") : t("rooms.addRoom")}
        </Button>
      </div>
    </Dialog>
  );
}
