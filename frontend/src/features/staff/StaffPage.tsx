import { useState } from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle, KeyRound, Pencil, Plus } from "lucide-react";
import toast from "react-hot-toast";

import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import { parseApiError } from "@/api/errors";
import { useResetStaffAccess, useStaff } from "@/features/staff/hooks";
import { StaffFormDialog } from "@/features/staff/components/StaffFormDialog";
import type { StaffOut } from "@/types/models";

export function StaffPage() {
  const { t } = useTranslation();
  const { data: staff, isLoading, isError } = useStaff();
  const resetAccess = useResetStaffAccess();
  const [formOpen, setFormOpen] = useState(false);
  const [editingStaff, setEditingStaff] = useState<StaffOut | null>(null);

  const handleResetAccess = async (member: StaffOut) => {
    if (!window.confirm(t("staffAdmin.confirmReset", { name: member.first_name }))) return;
    try {
      await resetAccess.mutateAsync(member.id);
      toast.success(t("staffAdmin.accessReset"));
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  return (
    <div>
      <PageHeader
        title={t("nav.staff")}
        subtitle={t("staffAdmin.subtitle")}
        actions={
          <Button
            onClick={() => {
              setEditingStaff(null);
              setFormOpen(true);
            }}
          >
            <Plus size={16} />
            {t("staffAdmin.addStaff")}
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
          <p className="text-sm font-medium">{t("staffAdmin.loadError")}</p>
        </div>
      )}

      {!isLoading && !isError && (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <th className="px-4 py-3">{t("common.firstName")}</th>
                  <th className="px-4 py-3">{t("common.email")}</th>
                  <th className="px-4 py-3">{t("common.mobile")}</th>
                  <th className="px-4 py-3">{t("profile.role")}</th>
                  <th className="px-4 py-3">{t("menuAdmin.isActive")}</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {(staff ?? []).map((member) => (
                  <tr key={member.id} className="border-b border-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-800">
                      {member.first_name} {member.last_name}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{member.email}</td>
                    <td className="px-4 py-3 text-slate-600">{member.mobile}</td>
                    <td className="px-4 py-3 text-slate-600">{t(`roles.${member.role}`)}</td>
                    <td className="px-4 py-3">
                      {member.is_active ? (
                        <span className="rounded-full bg-success-50 px-2 py-0.5 text-xs font-semibold text-success-700">
                          {t("staffAdmin.active")}
                        </span>
                      ) : (
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-500">
                          {t("staffAdmin.inactive")}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {member.role !== "OWNER" && (
                          <>
                            <button
                              type="button"
                              onClick={() => {
                                setEditingStaff(member);
                                setFormOpen(true);
                              }}
                              className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus-ring"
                              aria-label={t("staffAdmin.editStaff")}
                            >
                              <Pencil size={14} />
                            </button>
                            <button
                              type="button"
                              onClick={() => void handleResetAccess(member)}
                              className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus-ring"
                              aria-label={t("staffAdmin.resetAccess")}
                            >
                              <KeyRound size={14} />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <StaffFormDialog open={formOpen} staff={editingStaff} onClose={() => setFormOpen(false)} />
    </div>
  );
}
