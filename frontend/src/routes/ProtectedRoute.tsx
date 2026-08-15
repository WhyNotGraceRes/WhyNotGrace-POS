import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import { useAuthBootstrap } from "@/hooks/useAuthBootstrap";
import { FullPageSpinner } from "@/components/FullPageSpinner";

export function ProtectedRoute() {
  const hydrated = useAuthBootstrap();
  const accessToken = useAuthStore((s) => s.accessToken);
  const location = useLocation();

  if (!hydrated) {
    return <FullPageSpinner />;
  }

  if (!accessToken) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  return <Outlet />;
}
