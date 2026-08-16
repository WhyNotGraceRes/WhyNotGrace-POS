import { Navigate, Outlet, useLocation } from "react-router-dom";
import { usePlatformAuthStore } from "@/stores/platformAuthStore";
import { usePlatformAuthBootstrap } from "@/hooks/usePlatformAuthBootstrap";
import { FullPageSpinner } from "@/components/FullPageSpinner";

/** Platform counterpart to ProtectedRoute.tsx, keyed off
 * platformAuthStore instead of authStore — a business session never
 * satisfies this, and vice versa (see backend/app/core/platform_dependencies.py). */
export function PlatformProtectedRoute() {
  const hydrated = usePlatformAuthBootstrap();
  const accessToken = usePlatformAuthStore((s) => s.accessToken);
  const location = useLocation();

  if (!hydrated) {
    return <FullPageSpinner />;
  }

  if (!accessToken) {
    return <Navigate to="/platform/login" state={{ from: location.pathname }} replace />;
  }

  return <Outlet />;
}
