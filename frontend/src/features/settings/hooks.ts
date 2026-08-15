import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { featureFlagsApi } from "@/api/featureFlags";
import { businessSettingsApi } from "@/api/settings";
import type { BusinessSettingsUpdateRequest, FeatureModule } from "@/types/models";

export function useFeatureFlags() {
  return useQuery({
    queryKey: ["feature-flags"],
    queryFn: ({ signal }) => featureFlagsApi.list(signal),
    staleTime: 60_000,
  });
}

/** Convenience: is a given module enabled for the current business?
 * Defaults to false while loading/unknown — UI must fail closed, never
 * show a feature as available before we've actually confirmed it is. */
export function useIsFeatureEnabled(module: FeatureModule): boolean {
  const { data } = useFeatureFlags();
  return data?.find((f) => f.module === module)?.enabled ?? false;
}

export function useUpdateFeatureFlag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ module, enabled }: { module: FeatureModule; enabled: boolean }) =>
      featureFlagsApi.update(module, { enabled }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["feature-flags"] }),
  });
}

export function useBusinessSettings() {
  return useQuery({
    queryKey: ["business-settings"],
    queryFn: ({ signal }) => businessSettingsApi.get(signal),
    staleTime: 60_000,
  });
}

export function useUpdateBusinessSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: BusinessSettingsUpdateRequest) => businessSettingsApi.update(payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["business-settings"] }),
  });
}
