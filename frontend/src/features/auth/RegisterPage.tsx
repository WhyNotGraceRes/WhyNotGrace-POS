import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";

import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { FieldError } from "@/components/ui/FieldError";
import { parseApiError } from "@/api/errors";
import { businessTypeValues, registerSchema, type RegisterFormValues } from "@/features/auth/schemas";
import { useRegister } from "@/features/auth/hooks";

export function RegisterPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const register_ = useRegister();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { business_type: "RESTAURANT" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      const result = await register_.mutateAsync(values);
      toast.success(t("auth.register.success"));
      navigate(`/verify-email?email=${encodeURIComponent(result.email)}`, { replace: true });
    } catch (err) {
      setFormError(parseApiError(err).message);
    }
  });

  return (
    <Card className="p-8">
      <h1 className="text-2xl font-bold text-slate-900">{t("auth.register.title")}</h1>
      <p className="mt-1.5 text-sm text-slate-500">{t("auth.register.subtitle")}</p>

      <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
        {formError && (
          <div className="rounded-lg border border-danger-500/30 bg-danger-50 px-3 py-2 text-sm text-danger-700">
            {formError}
          </div>
        )}

        <div>
          <Label htmlFor="business_name">{t("auth.register.businessName")}</Label>
          <Input
            id="business_name"
            invalid={Boolean(errors.business_name)}
            {...register("business_name")}
          />
          <FieldError message={errors.business_name?.message} />
        </div>

        <div>
          <Label htmlFor="business_type">{t("auth.register.businessType")}</Label>
          <select
            id="business_type"
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 focus-ring hover:border-slate-400"
            {...register("business_type")}
          >
            {businessTypeValues.map((value) => (
              <option key={value} value={value}>
                {t(`auth.register.businessTypes.${value}`)}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="owner_first_name">{t("common.firstName")}</Label>
            <Input
              id="owner_first_name"
              invalid={Boolean(errors.owner_first_name)}
              {...register("owner_first_name")}
            />
            <FieldError message={errors.owner_first_name?.message} />
          </div>
          <div>
            <Label htmlFor="owner_last_name">{t("common.lastName")}</Label>
            <Input
              id="owner_last_name"
              invalid={Boolean(errors.owner_last_name)}
              {...register("owner_last_name")}
            />
            <FieldError message={errors.owner_last_name?.message} />
          </div>
        </div>

        <div>
          <Label htmlFor="email">{t("common.email")}</Label>
          <Input id="email" type="email" autoComplete="email" invalid={Boolean(errors.email)} {...register("email")} />
          <FieldError message={errors.email?.message} />
        </div>

        <div>
          <Label htmlFor="mobile">{t("common.mobile")}</Label>
          <Input id="mobile" type="tel" invalid={Boolean(errors.mobile)} {...register("mobile")} />
          <FieldError message={errors.mobile?.message} />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="password">{t("common.password")}</Label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              invalid={Boolean(errors.password)}
              {...register("password")}
            />
            <FieldError message={errors.password?.message} />
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
        </div>

        <Button type="submit" className="w-full" size="lg" isLoading={register_.isPending}>
          {t("auth.register.submit")}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500">
        {t("auth.register.haveAccount")}{" "}
        <Link to="/login" className="font-semibold text-brand-700 hover:underline">
          {t("auth.register.loginLink")}
        </Link>
      </p>
    </Card>
  );
}
