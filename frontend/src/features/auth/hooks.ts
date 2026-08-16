import { useMutation, useQuery } from "@tanstack/react-query";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/stores/authStore";
import type { ForgotPasswordRequest, LoginRequest, ResetPasswordRequest } from "@/types/models";

export function useLogin() {
  const setSession = useAuthStore((s) => s.setSession);
  return useMutation({
    mutationFn: (payload: LoginRequest) => authApi.login(payload),
    onSuccess: (data) => setSession(data, data.user),
  });
}

export function useForgotPassword() {
  return useMutation({
    mutationFn: (payload: ForgotPasswordRequest) => authApi.forgotPassword(payload),
  });
}

export function useResetPassword() {
  return useMutation({
    mutationFn: (payload: ResetPasswordRequest) => authApi.resetPassword(payload),
  });
}

export function useLogout() {
  const { refreshToken, clearSession } = useAuthStore();
  return useMutation({
    mutationFn: () => {
      if (!refreshToken) return Promise.resolve({ message: "" });
      return authApi.logout({ refresh_token: refreshToken });
    },
    onSettled: () => clearSession(),
  });
}

/** Fetches the current user — used to keep the store's user in sync
 * (e.g. after a silent refresh where we didn't just log in via a form). */
export function useCurrentUser(enabled: boolean) {
  const setUser = useAuthStore((s) => s.setUser);
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: async ({ signal }) => {
      const user = await authApi.me(signal);
      setUser(user);
      return user;
    },
    enabled,
    staleTime: 5 * 60_000,
  });
}
