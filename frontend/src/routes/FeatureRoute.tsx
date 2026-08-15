import { Navigate, Outlet } from "react-router-dom";
import { useFeatureFlags } from "@/features/settings/hooks";
import { FullPageSpinner } from "@/components/FullPageSpinner";
import type { FeatureModule } from "@/types/models";

/**
 * Blocks direct navigation to a feature-flagged route when the module is
 * disabled — the backend is still the real authority (every endpoint
 * behind a flag enforces it server-side via require_feature), this just
 * avoids rendering a page that would immediately error out, and avoids
 * calling its APIs at all per the "no unnecessary calls when disabled"
 * requirement.
 */
export function FeatureRoute({ module }: { module: FeatureModule }) {
  const { data: flags, isLoading } = useFeatureFlags();

  // Fail closed: don't briefly flash a gated page before flags resolve.
  if (isLoading) return <FullPageSpinner />;

  const enabled = flags?.find((f) => f.module === module)?.enabled ?? false;
  if (!enabled) return <Navigate to="/" replace />;

  return <Outlet />;
}
