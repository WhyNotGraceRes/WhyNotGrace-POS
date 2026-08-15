import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";

import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { FieldError } from "@/components/ui/FieldError";
import { parseApiError } from "@/api/errors";
import { resetPasswordSchema, type ResetPasswordFormValues } from "@/features/auth/schemas";
import { useResetPassword } from "@/features/auth/hooks";

export function ResetPasswordPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const resetPassword = useResetPassword();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordFormValues>({ resolver: zodResolver(resetPasswordSchema) });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    if (!token) {
      setFormError("This reset link is missing its token. Request a new one.");
      return;
    }
    try {
      await resetPassword.mutateAsync({ token, ...values });
      toast.success(t("auth.resetPassword.success"));
      navigate("/login", { replace: true });
    } catch (err) {
      setFormError(parseApiError(err).message);
    }
  });

  return (
    <Card className="p-8">
      <h1 className="text-2xl font-bold text-slate-900">{t("auth.resetPassword.title")}</h1>

      <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
        {formError && (
          <div className="rounded-lg border border-danger-500/30 bg-danger-50 px-3 py-2 text-sm text-danger-700">
            {formError}
          </div>
        )}

        <div>
          <Label htmlFor="new_password">{t("auth.resetPassword.newPasswordLabel")}</Label>
          <Input
            id="new_password"
            type="password"
            autoComplete="new-password"
            invalid={Boolean(errors.new_password)}
            {...register("new_password")}
          />
          <FieldError message={errors.new_password?.message} />
        </div>

        <div>
          <Label htmlFor="confirm_password">{t("common.confirmPassword")}</Label>
          <Input
            id="confirm_password"
            type="password"
            autoComplete="new-password"
            invalid={Boolean(errors.confirm_password)}
            {...register("confirm_password")}
          />
          <FieldError message={errors.confirm_password?.message} />
        </div>

        <Button type="submit" className="w-full" size="lg" isLoading={resetPassword.isPending}>
          {t("auth.resetPassword.submit")}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500">
        <Link to="/login" className="font-semibold text-brand-700 hover:underline">
          {t("auth.forgotPassword.backToLogin")}
        </Link>
      </p>
    </Card>
  );
}
