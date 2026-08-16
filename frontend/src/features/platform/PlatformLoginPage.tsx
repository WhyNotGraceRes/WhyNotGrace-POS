import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import toast from "react-hot-toast";

import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { FieldError } from "@/components/ui/FieldError";
import { parseApiError } from "@/api/errors";
import { usePlatformLogin } from "@/features/platform/hooks";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
type FormValues = z.infer<typeof schema>;

/** Deliberately no "register" link and no public entry point here — a
 * platform account only ever comes from another platform admin creating
 * it directly (see backend/app/services/platform_auth_service.py). */
export function PlatformLoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const login = usePlatformLogin();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await login.mutateAsync(values);
      toast.success("Signed in.");
      const redirectTo = (location.state as { from?: string } | null)?.from ?? "/platform/businesses";
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setFormError(parseApiError(err).message);
    }
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4">
      <Card className="w-full max-w-sm p-8">
        <div className="mb-1 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-sm font-bold text-white">
            W
          </div>
          <span className="text-lg font-bold tracking-tight text-slate-900">WhyNotGrace Platform</span>
        </div>
        <p className="mb-6 text-sm text-slate-500">Staff sign-in — not a business account.</p>

        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          {formError && (
            <div className="rounded-lg border border-danger-500/30 bg-danger-50 px-3 py-2 text-sm text-danger-700">
              {formError}
            </div>
          )}

          <div>
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="username"
              invalid={Boolean(errors.email)}
              {...register("email")}
            />
            <FieldError message={errors.email?.message} />
          </div>

          <div>
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              invalid={Boolean(errors.password)}
              {...register("password")}
            />
            <FieldError message={errors.password?.message} />
          </div>

          <Button type="submit" className="w-full" size="lg" isLoading={login.isPending}>
            Sign in
          </Button>
        </form>
      </Card>
    </div>
  );
}
