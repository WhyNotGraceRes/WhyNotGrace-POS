import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { UserOut } from "@/types/models";

/**
 * Session state.
 *
 * Security note: the backend issues JSON access/refresh tokens (no
 * httpOnly cookie support — see backend/app/api/auth.py). Given that
 * constraint, the access token is kept in memory only (never persisted),
 * and the refresh token is persisted to localStorage so a page reload
 * doesn't force a re-login. This is the standard tradeoff for a SPA
 * talking to a JSON-token auth API without cookie support; it is not
 * modified here since changing that contract means changing the backend,
 * which is out of scope. Do not add anything more sensitive to storage.
 */
interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: UserOut | null;
  /** True once the initial session rehydration (silent refresh) has resolved. */
  hydrated: boolean;
  setSession: (tokens: { access_token: string; refresh_token: string }, user: UserOut) => void;
  setTokens: (tokens: { access_token: string; refresh_token: string }) => void;
  setUser: (user: UserOut) => void;
  clearSession: () => void;
  setHydrated: (value: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      hydrated: false,
      setSession: (tokens, user) =>
        set({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token, user }),
      setTokens: (tokens) =>
        set({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token }),
      setUser: (user) => set({ user }),
      clearSession: () => set({ accessToken: null, refreshToken: null, user: null }),
      setHydrated: (value) => set({ hydrated: value }),
    }),
    {
      name: "whynotgrace-auth",
      // Only the refresh token + user survive a reload; the access token
      // is re-derived via a silent refresh on boot (see useAuthBootstrap).
      partialize: (state) => ({ refreshToken: state.refreshToken, user: state.user }),
    }
  )
);

export const isAuthenticated = () => Boolean(useAuthStore.getState().accessToken);
