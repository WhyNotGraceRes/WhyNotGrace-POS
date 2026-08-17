import { useState } from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle, Pencil, Plus, QrCode, Trash2, Users } from "lucide-react";
import toast from "react-hot-toast";

import { PageHeader } from "@/components/PageHeader";
import { FreshnessIndicator } from "@/components/FreshnessIndicator";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { cn } from "@/lib/cn";
import { parseApiError } from "@/api/errors";
import { useDeleteTable, useTables } from "@/features/tables/hooks";
import { TableFormDialog } from "@/features/tables/components/TableFormDialog";
import type { LocationOut, LocationStatus } from "@/types/models";

const STATUS_CLASSES: Record<LocationStatus, string> = {
  AVAILABLE: "border-success-300 bg-success-50 text-success-700",
  OCCUPIED: "border-warning-300 bg-warning-50 text-warning-700",
  ORDERING: "border-warning-300 bg-warning-50 text-warning-700",
  KITCHEN: "border-brand-300 bg-brand-50 text-brand-700",
  READY: "border-brand-300 bg-brand-50 text-brand-700",
  SERVED: "border-brand-300 bg-brand-50 text-brand-700",
  BILL_PENDING: "border-danger-300 bg-danger-50 text-danger-700",
  PAID: "border-stone-300 bg-stone-100 text-stone-500",
  CLOSED: "border-stone-300 bg-stone-100 text-stone-500",
};

export function TablesPage() {
  const { t } = useTranslation();
  const { data: tables, isLoading, isError, isFetching, dataUpdatedAt, refetch } = useTables();
  const deleteTable = useDeleteTable();
  const [qrTable, setQrTable] = useState<LocationOut | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editingTable, setEditingTable] = useState<LocationOut | null>(null);

  const handleDelete = async (table: LocationOut) => {
    if (!window.confirm(t("tables.confirmDelete", { name: table.name }))) return;
    try {
      await deleteTable.mutateAsync(table.id);
      toast.success(t("tables.tableDeleted"));
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  return (
    <div>
      <PageHeader
        title={t("nav.tables")}
        actions={
          <div className="flex items-center gap-3">
            {tables && (
              <FreshnessIndicator dataUpdatedAt={dataUpdatedAt} isFetching={isFetching} onRefresh={() => void refetch()} />
            )}
            <Button
              onClick={() => {
                setEditingTable(null);
                setFormOpen(true);
              }}
            >
              <Plus size={16} />
              {t("tables.addTable")}
            </Button>
          </div>
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
          <p className="text-sm font-medium">{t("pos.tablesLoadError")}</p>
        </div>
      )}

      {!isLoading && !isError && tables && tables.length === 0 && (
        <p className="py-16 text-center text-sm text-stone-400">{t("pos.noTables")}</p>
      )}

      {!isLoading && !isError && tables && tables.length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {tables.map((table) => (
            <Card
              key={table.id}
              className={cn("group relative flex flex-col items-center gap-1.5 border-2 p-4", STATUS_CLASSES[table.status])}
            >
              <span className="absolute right-1.5 top-1.5 hidden items-center gap-0.5 group-hover:flex">
                <button
                  type="button"
                  onClick={() => {
                    setEditingTable(table);
                    setFormOpen(true);
                  }}
                  className="rounded p-1 hover:bg-white/70"
                  aria-label={t("tables.editTable")}
                >
                  <Pencil size={12} />
                </button>
                <button
                  type="button"
                  onClick={() => void handleDelete(table)}
                  className="rounded p-1 hover:bg-white/70"
                  aria-label={t("tables.deleteTable")}
                >
                  <Trash2 size={12} />
                </button>
              </span>
              <span className="text-base font-bold">{table.name}</span>
              <span className="text-[11px] font-semibold uppercase tracking-wide opacity-75">
                {t(`tableStatus.${table.status}`)}
              </span>
              {table.capacity != null && (
                <span className="mt-1 flex items-center gap-1 text-xs opacity-70">
                  <Users size={12} /> {table.capacity}
                </span>
              )}
              {table.qr_url && (
                <button
                  type="button"
                  onClick={() => setQrTable(table)}
                  className="mt-1 flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-semibold opacity-80 hover:bg-white/60 hover:opacity-100 focus-ring"
                >
                  <QrCode size={12} /> {t("tables.qrLink")}
                </button>
              )}
            </Card>
          ))}
        </div>
      )}

      <Dialog open={Boolean(qrTable)} onClose={() => setQrTable(null)} title={t("tables.qrDialogTitle", { name: qrTable?.name })} size="sm">
        {qrTable?.qr_url && (
          <div className="space-y-3">
            <p className="text-sm text-stone-500">{t("tables.qrDialogHint")}</p>
            <p className="break-all rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs text-stone-700">
              {qrTable.qr_url}
            </p>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                className="flex-1"
                onClick={() => {
                  void navigator.clipboard.writeText(qrTable.qr_url as string);
                  toast.success(t("tables.qrLinkCopied"));
                }}
              >
                {t("tables.copyLink")}
              </Button>
              <a href={qrTable.qr_url} target="_blank" rel="noreferrer" className="flex-1">
                <Button className="w-full">{t("tables.openLink")}</Button>
              </a>
            </div>
          </div>
        )}
      </Dialog>

      <TableFormDialog open={formOpen} table={editingTable} onClose={() => setFormOpen(false)} />
    </div>
  );
}
