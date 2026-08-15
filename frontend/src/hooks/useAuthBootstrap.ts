import { useEffect } from "react";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/stores/authStore";

/**
 * Module-level (not component-level) in-flight guard. React 19 StrictMode
 * intentionally double-invokes effects in development, which — without
 * this guard — fires two concurrent /auth/refresh calls using the same
 * persisted refresh token. The backend correctly treats that as token
 * reuse (a theft signal, see auth_service.rotate_refresh_token) and
 * revokes the whole session, which raced against the legitimate refresh
 * and intermittently logged the user straight back out on page load.
 * A single shared promise means only one real request is ever made,
 * however many times the effect body runs.
 */
let bootstrapPromise: Promise<void> | null = null;

/**
 * Runs once on app load. If a refresh token survived from a previous
 * session (persisted in localStorage — see stores/authStore.ts), silently
 * exchange it for a fresh access token so the user doesn't have to log in
 * again on every page reload. Access tokens are never persisted, so this
 * is the only way a reload can resume an authenticated session.
 */
export function useAuthBootstrap() {
  const hydrated = useAuthStore((s) => s.hydrated);

  useEffect(() => {
    if (hydrated) return;

    bootstrapPromise ??= (async () => {
      const { refreshToken, setTokens, clearSession, setHydrated } = useAuthStore.getState();
      if (!refreshToken) {
        setHydrated(true);
        return;
      }
      try {
        const data = await authApi.refresh({ refresh_token: refreshToken });
        setTokens(data);
      } catch {
        clearSession();
      } finally {
        setHydrated(true);
      }
    })();
  }, [hydrated]);

  return hydrated;
}
