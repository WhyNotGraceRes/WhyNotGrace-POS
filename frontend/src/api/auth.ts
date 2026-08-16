import { apiClient } from "@/api/client";
import type {
  AccessTokenResponse,
  ForgotPasswordRequest,
  GenericMessageResponse,
  LoginRequest,
  LogoutRequest,
  RefreshRequest,
  ResetPasswordRequest,
  TokenPairResponse,
  UserOut,
} from "@/types/models";

export const authApi = {
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
