import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { PlatformUserOut } from "@/types/models";

/**
 * Session state for WhyNotGrace's own staff — structurally separate from
 * stores/authStore.ts (a business's own session), with its own localStorage
 * key, so a platform session and a business session can never collide or
 * be confused in the same browser. See backend/app/models/platform_user.py
 * for why the backend keeps these as two different principals entirely.
 *
 * Same access-token-in-memory-only / refresh-token-persisted tradeoff as
 * the business store, for the same reason (see that file).
 */
interface PlatformAuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: PlatformUserOut | null;
  hydrated: boolean;
  setSession: (tokens: { access_token: string; refresh_token: string }, user: PlatformUserOut) => void;
  setTokens: (tokens: { access_token: string; refresh_token: string }) => void;
  clearSession: () => void;
  setHydrated: (value: boolean) => void;
}

export const usePlatformAuthStore = create<PlatformAuthState>()(
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
      clearSession: () => set({ accessToken: null, refreshToken: null, user: null }),
      setHydrated: (value) => set({ hydrated: value }),
    }),
    {
      name: "whynotgrace-platform-auth",
      partialize: (state) => ({ refreshToken: state.refreshToken, user: state.user }),
    }
  )
);
