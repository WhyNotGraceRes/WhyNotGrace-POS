import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { QRScanResponse } from "@/types/models";

/**
 * Holds the ephemeral QR ordering session established by GET
 * /qr/scan/{business_slug}/{location_id} — never anything the customer's
 * browser invented itself. Persisted to sessionStorage (not localStorage)
 * so it survives an accidental refresh/tab-switch but never leaks into a
 * new tab or a later visit once the tab closes; the backend also expires
 * the token server-side (qr_session_expire_hours), so a stale value here
 * is harmless — every call re-validates against the backend.
 */
interface QrSessionState {
  sessionToken: string | null;
  businessSlug: string | null;
  businessId: string | null;
  businessName: string | null;
  locationId: string | null;
  locationName: string | null;
  locationType: string | null;
  expiresAt: string | null;
  setSession: (businessSlug: string, scan: QRScanResponse) => void;
  clearSession: () => void;
}

export const useQrSessionStore = create<QrSessionState>()(
  persist(
    (set) => ({
      sessionToken: null,
      businessSlug: null,
      businessId: null,
      businessName: null,
      locationId: null,
      locationName: null,
      locationType: null,
      expiresAt: null,

      setSession: (businessSlug, scan) =>
        set({
          sessionToken: scan.session_token,
          businessSlug,
          businessId: scan.business_id,
          businessName: scan.business_name,
          locationId: scan.location_id,
          locationName: scan.location_name,
          locationType: scan.location_type,
          expiresAt: scan.expires_at,
        }),

      clearSession: () =>
        set({
          sessionToken: null,
          businessSlug: null,
          businessId: null,
          businessName: null,
          locationId: null,
          locationName: null,
          locationType: null,
          expiresAt: null,
        }),
    }),
    {
      name: "whynotgrace-qr-session",
      storage: createJSONStorage(() => sessionStorage),
    }
  )
);

export function isQrSessionExpired(expiresAt: string | null): boolean {
  if (!expiresAt) return true;
  return new Date(expiresAt).getTime() <= Date.now();
}
