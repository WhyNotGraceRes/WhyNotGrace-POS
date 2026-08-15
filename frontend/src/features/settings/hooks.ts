import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { featureFlagsApi } from "@/api/featureFlags";
import { businessSettingsApi } from "@/api/settings";
import { chargesApi } from "@/api/charges";
import { togglesApi } from "@/api/toggles";
import type {
  BusinessSettingsUpdateRequest,
  ChargeBandCreate,
  ChargeBandUpdate,
  FeatureModule,
  PricingContext,
} from "@/types/models";

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

// --- Charge bands ---

export function useChargeBands() {
  return useQuery({
    queryKey: ["charge-bands"],
    queryFn: ({ signal }) => chargesApi.listBands(signal),
    staleTime: 30_000,
  });
}

export function useCreateChargeBand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ChargeBandCreate) => chargesApi.createBand(payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["charge-bands"] }),
  });
}

export function useUpdateChargeBand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ bandId, payload }: { bandId: string; payload: ChargeBandUpdate }) =>
      chargesApi.updateBand(bandId, payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["charge-bands"] }),
  });
}

export function useDeleteChargeBand() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (bandId: string) => chargesApi.deleteBand(bandId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["charge-bands"] }),
  });
}

/** What an order of `amount` would actually be charged, including how the
 * bands interact with tax. Disabled until an amount is entered so the owner
 * isn't shown a result for a value they never asked about. */
export function useChargePreview(amount: number | null, context: PricingContext | null) {
  return useQuery({
    queryKey: ["charge-preview", amount, context],
    queryFn: () => chargesApi.preview({ amount: amount ?? 0, context }),
    enabled: amount !== null && Number.isFinite(amount),
    staleTime: 0,
  });
}

// --- Fine-grained toggles ---

export function useToggles() {
  return useQuery({
    queryKey: ["toggles"],
    queryFn: ({ signal }) => togglesApi.list(signal),
    staleTime: 30_000,
  });
}

export function useUpdateToggle() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ key, enabled }: { key: string; enabled: boolean }) => togglesApi.update(key, enabled),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["toggles"] }),
  });
}

export function useResetToggle() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (key: string) => togglesApi.reset(key),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["toggles"] }),
  });
}

export function useInvoiceSeries() {
  return useQuery({
    queryKey: ["invoice-series"],
    queryFn: ({ signal }) => togglesApi.invoiceSeries(signal),
    staleTime: 30_000,
  });
}
