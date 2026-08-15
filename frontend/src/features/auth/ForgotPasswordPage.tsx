import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { FieldError } from "@/components/ui/FieldError";
import { parseApiError } from "@/api/errors";
import { forgotPasswordSchema, type ForgotPasswordFormValues } from "@/features/auth/schemas";
import { useForgotPassword } from "@/features/auth/hooks";

export function ForgotPasswordPage() {
  const { t } = useTranslation();
  const forgotPassword = useForgotPassword();
  const [message, setMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormValues>({ resolver: zodResolver(forgotPasswordSchema) });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      // Backend intentionally returns the same generic message whether or
      // not the account exists — the UI must not try to be smarter than that.
      const result = await forgotPassword.mutateAsync(values);
      setMessage(result.message);
    } catch (err) {
      setFormError(parseApiError(err).message);
    }
  });

  return (
    <Card className="p-8">
      <h1 className="text-2xl font-bold text-slate-900">{t("auth.forgotPassword.title")}</h1>
      <p className="mt-1.5 text-sm text-slate-500">{t("auth.forgotPassword.subtitle")}</p>

      {message ? (
        <div className="mt-6 rounded-lg border border-success-500/30 bg-success-50 px-3 py-3 text-sm text-success-600">
          {message}
        </div>
      ) : (
        <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
          {formError && (
            <div className="rounded-lg border border-danger-500/30 bg-danger-50 px-3 py-2 text-sm text-danger-700">
              {formError}
            </div>
          )}

          <div>
            <Label htmlFor="email">{t("common.email")}</Label>
            <Input id="email" type="email" autoComplete="email" invalid={Boolean(errors.email)} {...register("email")} />
            <FieldError message={errors.email?.message} />
          </div>

          <Button type="submit" className="w-full" size="lg" isLoading={forgotPassword.isPending}>
            {t("auth.forgotPassword.submit")}
          </Button>
        </form>
      )}

      <p className="mt-6 text-center text-sm text-slate-500">
        <Link to="/login" className="font-semibold text-brand-700 hover:underline">
          {t("auth.forgotPassword.backToLogin")}
        </Link>
      </p>
    </Card>
  );
}
