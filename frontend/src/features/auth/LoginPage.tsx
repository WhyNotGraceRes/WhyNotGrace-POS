import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";

import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { FieldError } from "@/components/ui/FieldError";
import { parseApiError } from "@/api/errors";
import { loginSchema, type LoginFormValues } from "@/features/auth/schemas";
import { useLogin } from "@/features/auth/hooks";

export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const login = useLogin();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await login.mutateAsync(values);
      toast.success(t("auth.login.success"));
      const redirectTo = (location.state as { from?: string } | null)?.from ?? "/";
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setFormError(parseApiError(err).message);
    }
  });

  return (
    <Card className="p-8">
      <h1 className="text-2xl font-bold text-stone-900">{t("auth.login.title")}</h1>
      <p className="mt-1.5 text-sm text-stone-500">{t("auth.login.subtitle")}</p>

      <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
        {formError && (
          <div className="rounded-lg border border-danger-500/30 bg-danger-50 px-3 py-2 text-sm text-danger-700">
            {formError}
          </div>
        )}

        <div>
          <Label htmlFor="identifier">{t("auth.login.identifierLabel")}</Label>
          <Input
            id="identifier"
            type="text"
            autoComplete="username"
            placeholder={t("auth.login.identifierPlaceholder")}
            invalid={Boolean(errors.identifier)}
            {...register("identifier")}
          />
          <FieldError message={errors.identifier?.message} />
        </div>

        <div>
          <div className="flex items-center justify-between">
            <Label htmlFor="password">{t("common.password")}</Label>
            <Link to="/forgot-password" className="mb-1.5 text-xs font-medium text-brand-700 hover:underline">
              {t("auth.login.forgotPassword")}
            </Link>
          </div>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            placeholder={t("auth.login.passwordPlaceholder")}
            invalid={Boolean(errors.password)}
            {...register("password")}
          />
          <FieldError message={errors.password?.message} />
        </div>

        <Button type="submit" className="w-full" size="lg" isLoading={login.isPending}>
          {t("auth.login.submit")}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-stone-500">{t("auth.login.noAccount")}</p>
    </Card>
  );
}
