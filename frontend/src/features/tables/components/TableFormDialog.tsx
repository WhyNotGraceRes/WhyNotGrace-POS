import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";

import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Switch } from "@/components/ui/Switch";
import { parseApiError } from "@/api/errors";
import { useCreateTable, useUpdateTable } from "@/features/tables/hooks";
import type { LocationOut } from "@/types/models";

export function TableFormDialog({
  open,
  table,
  onClose,
}: {
  open: boolean;
  table: LocationOut | null;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const createTable = useCreateTable();
  const updateTable = useUpdateTable();
  const isEdit = Boolean(table);

  const [name, setName] = useState(table?.name ?? "");
  const [capacity, setCapacity] = useState(table?.capacity != null ? String(table.capacity) : "");
  const [floor, setFloor] = useState(table?.floor ?? "");
  const [isActive, setIsActive] = useState(table?.is_active ?? true);
  const [error, setError] = useState<string | null>(null);

  const [openId, setOpenId] = useState<string | null>(table?.id ?? null);
  if (open && (table?.id ?? null) !== openId) {
    setOpenId(table?.id ?? null);
    setName(table?.name ?? "");
    setCapacity(table?.capacity != null ? String(table.capacity) : "");
    setFloor(table?.floor ?? "");
    setIsActive(table?.is_active ?? true);
    setError(null);
  }

  const isPending = createTable.isPending || updateTable.isPending;

  const handleSubmit = async () => {
    setError(null);
    if (!name.trim()) {
      setError(t("tables.nameRequired"));
      return;
    }
    try {
      if (isEdit && table) {
        await updateTable.mutateAsync({
          tableId: table.id,
          payload: {
            name: name.trim(),
            capacity: capacity ? Number(capacity) : null,
            floor: floor.trim() || null,
            is_active: isActive,
          },
        });
        toast.success(t("tables.tableUpdated"));
      } else {
        await createTable.mutateAsync({ name: name.trim(), capacity: capacity ? Number(capacity) : undefined, floor: floor.trim() || undefined });
        toast.success(t("tables.tableCreated"));
      }
      onClose();
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title={isEdit ? t("tables.editTable") : t("tables.addTable")} size="sm">
      <div className="space-y-3">
        {error && <p className="text-xs text-danger-600">{error}</p>}
        <div>
          <Label htmlFor="table-name">{t("tables.tableName")}</Label>
          <Input id="table-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="T1" />
        </div>
        <div>
          <Label htmlFor="table-capacity">{t("tables.capacity")}</Label>
          <Input id="table-capacity" type="number" min={1} value={capacity} onChange={(e) => setCapacity(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="table-floor">{t("tables.floor")}</Label>
          <Input id="table-floor" value={floor} onChange={(e) => setFloor(e.target.value)} />
        </div>
        {isEdit && (
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <Switch checked={isActive} onChange={setIsActive} label={t("menuAdmin.isActive")} />
            {t("menuAdmin.isActive")}
          </label>
        )}
        <Button className="w-full" isLoading={isPending} onClick={() => void handleSubmit()}>
          {isEdit ? t("common.save") : t("tables.addTable")}
        </Button>
      </div>
    </Dialog>
  );
}
