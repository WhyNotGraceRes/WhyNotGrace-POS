import { Outlet } from "react-router-dom";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { useQrSessionStore } from "@/stores/qrSessionStore";

/**
 * Top-level shell for the public customer QR ordering experience — no
 * staff sidebar, no auth-gated chrome, nothing an unauthenticated visitor
 * shouldn't see. Deliberately narrow (phone-width column, centered) even
 * on a wide desktop preview, since this is designed to be opened almost
 * exclusively on a phone after scanning a table QR code.
 */
export function QrLayout() {
  const businessName = useQrSessionStore((s) => s.businessName);
  const locationName = useQrSessionStore((s) => s.locationName);

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto flex min-h-screen w-full max-w-md flex-col bg-white shadow-sm">
        <header className="sticky top-0 z-40 flex items-center justify-between gap-2 border-b border-slate-100 bg-white/95 px-4 py-3 backdrop-blur">
          <div className="min-w-0">
            <p className="truncate text-sm font-bold text-slate-900">{businessName ?? "WhyNotGrace"}</p>
            {locationName && <p className="truncate text-xs text-slate-500">{locationName}</p>}
          </div>
          <LanguageSwitcher className="shrink-0" />
        </header>

        <main className="flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
