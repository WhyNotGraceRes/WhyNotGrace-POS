import { NavLink, Outlet } from "react-router-dom";
import { LogOut } from "lucide-react";

import { usePlatformAuthStore } from "@/stores/platformAuthStore";
import { usePlatformLogout } from "@/features/platform/hooks";

/** Its own shell — deliberately not AppLayout (no restaurant sidebar/nav,
 * no business-scoped nav items) — see the plan for why this is a separate
 * route tree in the same app rather than a second deployable frontend. */
export function PlatformLayout() {
  const user = usePlatformAuthStore((s) => s.user);
  const logout = usePlatformLogout();

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="flex items-center justify-between border-b border-slate-200 bg-slate-950 px-6 py-3">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-white text-xs font-bold text-slate-900">
              W
            </div>
            <span className="text-sm font-bold tracking-tight text-white">WhyNotGrace Platform</span>
          </div>
          <NavLink
            to="/platform/businesses"
            className={({ isActive }) =>
              `text-sm font-medium ${isActive ? "text-white" : "text-slate-400 hover:text-slate-200"}`
            }
          >
            Businesses
          </NavLink>
        </div>

        <div className="flex items-center gap-3 text-sm text-slate-300">
          <span>{user ? `${user.first_name} ${user.last_name}` : ""}</span>
          <button
            type="button"
            onClick={() => logout.mutate()}
            className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-slate-300 hover:bg-white/10 hover:text-white"
          >
            <LogOut size={15} />
            Sign out
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl p-4 sm:p-6">
        <Outlet />
      </main>
    </div>
  );
}
