import { useEffect } from "react";
import { platformAuthApi } from "@/api/platform";
import { usePlatformAuthStore } from "@/stores/platformAuthStore";

/** Platform counterpart to useAuthBootstrap.ts — same silent-refresh-on-load
 * shape and the same StrictMode double-invoke guard, kept entirely separate
 * so it can never race with or clear the business session's bootstrap. */
let bootstrapPromise: Promise<void> | null = null;

export function usePlatformAuthBootstrap() {
  const hydrated = usePlatformAuthStore((s) => s.hydrated);

  useEffect(() => {
    if (hydrated) return;

    bootstrapPromise ??= (async () => {
      const { refreshToken, setTokens, clearSession, setHydrated } = usePlatformAuthStore.getState();
      if (!refreshToken) {
        setHydrated(true);
        return;
      }
      try {
        const data = await platformAuthApi.refresh({ refresh_token: refreshToken });
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
