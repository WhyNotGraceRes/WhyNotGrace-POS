import { useTranslation } from "react-i18next";
import { CheckCircle2, XCircle } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAuthStore } from "@/stores/authStore";
import { useBusiness } from "@/features/business/hooks";
import { useLogout } from "@/features/auth/hooks";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-slate-100 py-3 last:border-0">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="text-sm font-medium text-slate-800">{children}</span>
    </div>
  );
}

export function ProfilePage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const { data: business } = useBusiness();
  const logout = useLogout();

  if (!user) return null;

  return (
    <div>
      <PageHeader title={t("shell.profile")} />

      <Card className="max-w-lg p-5">
        <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-100 text-lg font-bold text-brand-700">
            {user.first_name[0]}
            {user.last_name[0]}
          </div>
          <div>
            <p className="font-bold text-slate-900">
              {user.first_name} {user.last_name}
            </p>
            <p className="text-sm text-slate-500">{t(`roles.${user.role}`)}</p>
          </div>
        </div>

        <div className="pt-1">
          <Row label={t("profile.email")}>
            <span className="flex items-center gap-1.5">
              {user.email}
              {user.is_email_verified ? (
                <CheckCircle2 size={14} className="text-success-500" aria-label={t("profile.emailVerified")} />
              ) : (
                <XCircle size={14} className="text-danger-500" aria-label={t("profile.emailNotVerified")} />
              )}
            </span>
          </Row>
          <Row label={t("profile.mobile")}>{user.mobile}</Row>
          <Row label={t("profile.role")}>{t(`roles.${user.role}`)}</Row>
          <Row label={t("profile.business")}>{business?.name ?? "—"}</Row>
        </div>

        <Button variant="secondary" className="mt-5 w-full" onClick={() => logout.mutate()} isLoading={logout.isPending}>
          {t("shell.logout")}
        </Button>
      </Card>
    </div>
  );
}
