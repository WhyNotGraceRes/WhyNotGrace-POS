import { z } from "zod";

// Mirrors backend/app/schemas/auth.py exactly — do not loosen/invent
// constraints here beyond what the API actually enforces. There is no
// self-registration any more (see backend/app/api/platform/businesses.py) —
// business_type/mobile validation for provisioning lives in
// src/features/platform instead.

export const loginSchema = z.object({
  identifier: z.string().min(3, "Enter your email or mobile number"),
  password: z.string().min(1, "Password is required"),
});
export type LoginFormValues = z.infer<typeof loginSchema>;

export const forgotPasswordSchema = z.object({
  email: z.string().email(),
});
export type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>;

export const resetPasswordSchema = z
  .object({
    new_password: z.string().min(8).max(128),
    confirm_password: z.string().min(8).max(128),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });
export type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>;
