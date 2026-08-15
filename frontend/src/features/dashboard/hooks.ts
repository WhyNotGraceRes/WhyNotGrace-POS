import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/api/dashboard";
import { useAuthStore } from "@/stores/authStore";

const DASHBOARD_ROLES = new Set(["OWNER", "MANAGER"]);

export function useDashboard() {
  const role = useAuthStore((s) => s.user?.role);
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: ({ signal }) => dashboardApi.get(signal),
    // The backend restricts GET /dashboard to OWNER/MANAGER (see
    // backend/app/api/dashboard.py). Calling it for any other role would
    // just be a guaranteed 403 — don't even try.
    enabled: role ? DASHBOARD_ROLES.has(role) : false,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}
