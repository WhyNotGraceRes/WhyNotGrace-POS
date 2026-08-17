import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "@/components/shell/Sidebar";
import { Header } from "@/components/shell/Header";
import { SubscriptionBanner } from "@/components/shell/SubscriptionBanner";

/** Shell for the authenticated area: responsive sidebar + header + content. */
export function AppLayout() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setMobileNavOpen(false);
  }, [location.pathname]);

  return (
    <div className="flex h-screen overflow-hidden bg-stone-50">
      <Sidebar mobileOpen={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />

      <div className="flex min-w-0 flex-1 flex-col">
        <SubscriptionBanner />
        <Header onMenuClick={() => setMobileNavOpen(true)} />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
