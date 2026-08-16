import { apiClient } from "@/api/client";
import type { FeatureFlagOut } from "@/types/models";

/** Read-only — see backend/app/api/feature_flags.py. What a business is
 * entitled to is set by platform staff (src/api/platform.ts), not the
 * business itself. */
export const featureFlagsApi = {
  list: (signal?: AbortSignal) =>
    apiClient.get<FeatureFlagOut[]>("/settings/features", { signal }).then((r) => r.data),
};
