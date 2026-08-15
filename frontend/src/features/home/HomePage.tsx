import { useAuthStore } from "@/stores/authStore";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { RoleHomePage } from "@/features/home/RoleHomePage";

const DASHBOARD_ROLES = new Set(["OWNER", "MANAGER"]);

/** Routed at "/". Picks the real dashboard for OWNER/MANAGER (the only
 * roles the backend grants GET /dashboard to) and a role-appropriate
 * landing page for everyone else. */
export function HomePage() {
  const role = useAuthStore((s) => s.user?.role);
  return role && DASHBOARD_ROLES.has(role) ? <DashboardPage /> : <RoleHomePage />;
}
