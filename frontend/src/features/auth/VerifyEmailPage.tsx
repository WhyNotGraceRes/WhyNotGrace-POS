import { useEffect, useState } from "react";
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
import { verifyEmailSchema, type VerifyEmailFormValues } from "@/features/auth/schemas";
import { useResendVerification, useVerifyEmail } from "@/features/auth/hooks";

const RESEND_COOLDOWN_SECONDS = 60;

export function VerifyEmailPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const email = searchParams.get("email") ?? "";

  const verifyEmail = useVerifyEmail();
  const resend = useResendVerification();
  const [formError, setFormError] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState(0);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<VerifyEmailFormValues>({
    resolver: zodResolver(verifyEmailSchema),
    defaultValues: { email },
  });

  useEffect(() => {
    if (cooldown <= 0) return;
    const id = setInterval(() => setCooldown((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [cooldown]);

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await verifyEmail.mutateAsync(values);
      toast.success(t("auth.verifyEmail.success"));
      navigate("/login", { replace: true });
    } catch (err) {
      setFormError(parseApiError(err).message);
    }
  });

  const onResend = async () => {
    try {
      await resend.mutateAsync({ email });
      toast.success(t("auth.verifyEmail.resend"));
      setCooldown(RESEND_COOLDOWN_SECONDS);
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  return (
    <Card className="p-8">
      <h1 className="text-2xl font-bold text-slate-900">{t("auth.verifyEmail.title")}</h1>
      <p className="mt-1.5 text-sm text-slate-500">{t("auth.verifyEmail.subtitle", { email })}</p>

      <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
        {formError && (
          <div className="rounded-lg border border-danger-500/30 bg-danger-50 px-3 py-2 text-sm text-danger-700">
            {formError}
          </div>
        )}

        <input type="hidden" {...register("email")} />

        <div>
          <Label htmlFor="code">{t("auth.verifyEmail.codeLabel")}</Label>
          <Input
            id="code"
            inputMode="numeric"
            maxLength={6}
            autoComplete="one-time-code"
            className="text-center text-lg tracking-[0.5em]"
            invalid={Boolean(errors.code)}
            {...register("code")}
          />
          <FieldError message={errors.code?.message} />
        </div>

        <Button type="submit" className="w-full" size="lg" isLoading={verifyEmail.isPending}>
          {t("auth.verifyEmail.submit")}
        </Button>
      </form>

      <button
        type="button"
        onClick={onResend}
        disabled={cooldown > 0 || resend.isPending}
        className="mt-4 w-full text-center text-sm font-medium text-brand-700 hover:underline disabled:cursor-not-allowed disabled:text-slate-400 disabled:no-underline"
      >
        {cooldown > 0 ? t("auth.verifyEmail.resendCooldown", { seconds: cooldown }) : t("auth.verifyEmail.resend")}
      </button>

      <p className="mt-6 text-center text-sm text-slate-500">
        <Link to="/login" className="font-semibold text-brand-700 hover:underline">
          {t("auth.forgotPassword.backToLogin")}
        </Link>
      </p>
    </Card>
  );
}
