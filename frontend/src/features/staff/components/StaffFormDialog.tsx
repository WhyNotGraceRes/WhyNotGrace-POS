import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";

import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { Switch } from "@/components/ui/Switch";
import { parseApiError } from "@/api/errors";
import { useCreateStaff, useUpdateStaff } from "@/features/staff/hooks";
import type { StaffOut, UserRole } from "@/types/models";

const ASSIGNABLE_ROLES: UserRole[] = ["MANAGER", "CASH_COUNTER", "SERVICE_COUNTER", "KITCHEN", "DELIVERY"];

export function StaffFormDialog({
  open,
  staff,
  onClose,
}: {
  open: boolean;
  staff: StaffOut | null;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const createStaff = useCreateStaff();
  const updateStaff = useUpdateStaff();
  const isEdit = Boolean(staff);

  const [firstName, setFirstName] = useState(staff?.first_name ?? "");
  const [lastName, setLastName] = useState(staff?.last_name ?? "");
  const [email, setEmail] = useState(staff?.email ?? "");
  const [mobile, setMobile] = useState(staff?.mobile ?? "");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>(staff?.role ?? "CASH_COUNTER");
  const [isActive, setIsActive] = useState(staff?.is_active ?? true);
  const [error, setError] = useState<string | null>(null);

  const [openId, setOpenId] = useState<string | null>(staff?.id ?? null);
  if (open && (staff?.id ?? null) !== openId) {
    setOpenId(staff?.id ?? null);
    setFirstName(staff?.first_name ?? "");
    setLastName(staff?.last_name ?? "");
    setEmail(staff?.email ?? "");
    setMobile(staff?.mobile ?? "");
    setPassword("");
    setRole(staff?.role ?? "CASH_COUNTER");
    setIsActive(staff?.is_active ?? true);
    setError(null);
  }

  const isPending = createStaff.isPending || updateStaff.isPending;

  const handleSubmit = async () => {
    setError(null);
    if (isEdit && staff) {
      try {
        await updateStaff.mutateAsync({
          staffId: staff.id,
          payload: { first_name: firstName.trim(), last_name: lastName.trim(), role, is_active: isActive },
        });
        toast.success(t("staffAdmin.staffUpdated"));
        onClose();
      } catch (err) {
        setError(parseApiError(err).message);
      }
      return;
    }

    if (!firstName.trim() || !lastName.trim() || !email.trim() || mobile.trim().length < 7 || password.length < 8) {
      setError(t("staffAdmin.fieldsInvalid"));
      return;
    }
    try {
      await createStaff.mutateAsync({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim(),
        mobile: mobile.trim(),
        password,
        role,
      });
      toast.success(t("staffAdmin.staffCreated"));
      onClose();
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title={isEdit ? t("staffAdmin.editStaff") : t("staffAdmin.addStaff")} size="sm">
      <div className="space-y-3">
        {error && <p className="text-xs text-danger-600">{error}</p>}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="staff-first">{t("common.firstName")}</Label>
            <Input id="staff-first" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="staff-last">{t("common.lastName")}</Label>
            <Input id="staff-last" value={lastName} onChange={(e) => setLastName(e.target.value)} />
          </div>
        </div>
        {!isEdit && (
          <>
            <div>
              <Label htmlFor="staff-email">{t("common.email")}</Label>
              <Input id="staff-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="staff-mobile">{t("common.mobile")}</Label>
              <Input id="staff-mobile" value={mobile} onChange={(e) => setMobile(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="staff-password">{t("staffAdmin.tempPassword")}</Label>
              <Input id="staff-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
          </>
        )}
        <div>
          <Label htmlFor="staff-role">{t("profile.role")}</Label>
          <Select id="staff-role" value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
            {ASSIGNABLE_ROLES.map((r) => (
              <option key={r} value={r}>
                {t(`roles.${r}`)}
              </option>
            ))}
          </Select>
        </div>
        {isEdit && (
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <Switch checked={isActive} onChange={setIsActive} label={t("menuAdmin.isActive")} />
            {t("menuAdmin.isActive")}
          </label>
        )}
        <Button className="w-full" isLoading={isPending} onClick={() => void handleSubmit()}>
          {isEdit ? t("common.save") : t("staffAdmin.addStaff")}
        </Button>
      </div>
    </Dialog>
  );
}
