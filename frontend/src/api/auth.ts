import { apiClient } from "@/api/client";
import type {
  AccessTokenResponse,
  ForgotPasswordRequest,
  GenericMessageResponse,
  LoginRequest,
  LogoutRequest,
  RefreshRequest,
  RegisterRequest,
  RegisterResponse,
  ResendVerificationRequest,
  ResetPasswordRequest,
  TokenPairResponse,
  UserOut,
  VerifyEmailRequest,
} from "@/types/models";

export const authApi = {
  register: (payload: RegisterRequest) =>
    apiClient.post<RegisterResponse>("/auth/register", payload).then((r) => r.data),

  verifyEmail: (payload: VerifyEmailRequest) =>
    apiClient.post<GenericMessageResponse>("/auth/verify-email", payload).then((r) => r.data),

  resendVerification: (payload: ResendVerificationRequest) =>
    apiClient.post<GenericMessageResponse>("/auth/resend-verification", payload).then((r) => r.data),

  login: (payload: LoginRequest) =>
    apiClient.post<TokenPairResponse>("/auth/login", payload).then((r) => r.data),

  refresh: (payload: RefreshRequest) =>
    apiClient.post<AccessTokenResponse>("/auth/refresh", payload).then((r) => r.data),

  logout: (payload: LogoutRequest) =>
    apiClient.post<GenericMessageResponse>("/auth/logout", payload).then((r) => r.data),

  forgotPassword: (payload: ForgotPasswordRequest) =>
    apiClient.post<GenericMessageResponse>("/auth/forgot-password", payload).then((r) => r.data),

  resetPassword: (payload: ResetPasswordRequest) =>
    apiClient.post<GenericMessageResponse>("/auth/reset-password", payload).then((r) => r.data),

  me: (signal?: AbortSignal) => apiClient.get<UserOut>("/auth/me", { signal }).then((r) => r.data),
};
