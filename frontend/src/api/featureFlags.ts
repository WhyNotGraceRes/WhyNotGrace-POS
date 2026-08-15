import { apiClient } from "@/api/client";
import type { FeatureFlagOut, FeatureFlagUpdateRequest, FeatureModule } from "@/types/models";

export const featureFlagsApi = {
  list: (signal?: AbortSignal) =>
    apiClient.get<FeatureFlagOut[]>("/settings/features", { signal }).then((r) => r.data),

  update: (module: FeatureModule, payload: FeatureFlagUpdateRequest) =>
    apiClient.put<FeatureFlagOut>(`/settings/features/${module}`, payload).then((r) => r.data),
};
