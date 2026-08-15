import { useEffect, useState } from "react";
import { qrApi } from "@/api/qr";
import { parseApiError } from "@/api/errors";
import { isQrSessionExpired, useQrSessionStore } from "@/stores/qrSessionStore";

type QrSessionStatus = "loading" | "ready" | "error";

/**
 * Establishes (or reuses) the QR ordering session for this business +
 * location. Never trusts anything the browser already has cached for a
 * *different* business/location — a fresh scan is required whenever the
 * route params change. The backend remains authoritative: a wrong/expired
 * `code` simply comes back as a real 403/404 from GET /qr/scan, never
 * something guessed or faked client-side.
 */
export function useQrSessionBootstrap(businessSlug: string, locationId: string, code: string | null) {
  const sessionToken = useQrSessionStore((s) => s.sessionToken);
  const storedBusinessSlug = useQrSessionStore((s) => s.businessSlug);
  const storedLocationId = useQrSessionStore((s) => s.locationId);
  const expiresAt = useQrSessionStore((s) => s.expiresAt);
  const setSession = useQrSessionStore((s) => s.setSession);

  const [status, setStatus] = useState<QrSessionStatus>("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const hasValidExisting =
    Boolean(sessionToken) &&
    storedBusinessSlug === businessSlug &&
    storedLocationId === locationId &&
    !isQrSessionExpired(expiresAt);

  useEffect(() => {
    if (hasValidExisting) {
      setStatus("ready");
      return;
    }

    if (!code) {
      setStatus("error");
      setErrorMessage(null);
      return;
    }

    setStatus("loading");
    setErrorMessage(null);
    const controller = new AbortController();

    qrApi
      .scan(businessSlug, locationId, code, controller.signal)
      .then((scan) => {
        setSession(businessSlug, scan);
        setStatus("ready");
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        setErrorMessage(parseApiError(err).message);
        setStatus("error");
      });

    return () => controller.abort();
  }, [businessSlug, locationId, code, hasValidExisting, setSession]);

  return { status, errorMessage };
}
