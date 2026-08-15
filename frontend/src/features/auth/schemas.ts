import { z } from "zod";

// Mirrors backend/app/schemas/auth.py exactly — do not loosen/invent
// constraints here beyond what the API actually enforces.

const mobileSchema = z
  .string()
  .min(7)
  .max(20)
  .refine((v) => /^[0-9+\-\s]+$/.test(v), "Mobile number must contain only digits, spaces, +, or -");

export const loginSchema = z.object({
  identifier: z.string().min(3, "Enter your email or mobile number"),
  password: z.string().min(1, "Password is required"),
});
export type LoginFormValues = z.infer<typeof loginSchema>;

export const businessTypeValues = [
  "RESTAURANT",
  "HOTEL",
  "RESORT",
  "LODGE",
  "LOUNGE",
  "CAFE",
  "CLOUD_KITCHEN",
  "OTHER",
] as const;

export const registerSchema = z
  .object({
    business_name: z.string().min(2).max(200),
    business_type: z.enum(businessTypeValues),
    owner_first_name: z.string().min(1).max(100),
    owner_last_name: z.string().min(1).max(100),
    email: z.string().email(),
    mobile: mobileSchema,
    password: z.string().min(8).max(128),
    confirm_password: z.string().min(8).max(128),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });
export type RegisterFormValues = z.infer<typeof registerSchema>;

export const verifyEmailSchema = z.object({
  email: z.string().email(),
  code: z.string().regex(/^\d{6}$/, "Enter the 6-digit code"),
});
export type VerifyEmailFormValues = z.infer<typeof verifyEmailSchema>;

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
