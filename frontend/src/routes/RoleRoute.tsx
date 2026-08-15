import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import type { UserRole } from "@/types/models";

/**
 * Additional UI-layer role gate on top of ProtectedRoute. This is a
 * convenience for showing the right screen per role — the backend
 * remains the sole authority; every request is still enforced there
 * regardless of what this component allows to render (see backend
 * app/core/dependencies.py:require_roles).
 */
export function RoleRoute({ allowedRoles }: { allowedRoles: UserRole[] }) {
  const role = useAuthStore((s) => s.user?.role);

  if (!role || !allowedRoles.includes(role)) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
