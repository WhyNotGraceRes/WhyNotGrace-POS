import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  platformAuthApi,
  platformBusinessesApi,
  platformFeaturesApi,
  platformSubscriptionApi,
  platformTogglesApi,
} from "@/api/platform";
import { usePlatformAuthStore } from "@/stores/platformAuthStore";
import type {
  FeatureModule,
  PlatformLoginRequest,
  ProvisionBusinessRequest,
  ProvisionSubscriptionRequest,
  RenewSubscriptionRequest,
} from "@/types/models";

export function usePlatformLogin() {
  const setSession = usePlatformAuthStore((s) => s.setSession);
  return useMutation({
    mutationFn: (payload: PlatformLoginRequest) => platformAuthApi.login(payload),
    onSuccess: (data) => setSession(data, data.user),
  });
}

export function usePlatformLogout() {
  const { refreshToken, clearSession } = usePlatformAuthStore();
  return useMutation({
    mutationFn: () => {
      if (!refreshToken) return Promise.resolve({ message: "" });
      return platformAuthApi.logout({ refresh_token: refreshToken });
    },
    onSettled: () => clearSession(),
  });
}

export function usePlatformBusinesses() {
  return useQuery({
    queryKey: ["platform", "businesses"],
    queryFn: ({ signal }) => platformBusinessesApi.list(signal),
    staleTime: 15_000,
  });
}

export function usePlatformBusiness(businessId: string | null) {
  return useQuery({
    queryKey: ["platform", "businesses", businessId],
    queryFn: ({ signal }) => platformBusinessesApi.get(businessId as string, signal),
    enabled: Boolean(businessId),
    staleTime: 15_000,
  });
}

export function useProvisionBusiness() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProvisionBusinessRequest) => platformBusinessesApi.provision(payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["platform", "businesses"] }),
  });
}

export function useSetBusinessActive() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ businessId, isActive }: { businessId: string; isActive: boolean }) =>
      platformBusinessesApi.setActive(businessId, { is_active: isActive }),
    onSuccess: (_data, { businessId }) => {
      void queryClient.invalidateQueries({ queryKey: ["platform", "businesses"] });
      void queryClient.invalidateQueries({ queryKey: ["platform", "businesses", businessId] });
    },
  });
}

export function usePlatformFeatures(businessId: string | null) {
  return useQuery({
    queryKey: ["platform", "features", businessId],
    queryFn: ({ signal }) => platformFeaturesApi.list(businessId as string, signal),
    enabled: Boolean(businessId),
    staleTime: 15_000,
  });
}

export function useSetPlatformFeature(businessId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ module, enabled }: { module: FeatureModule; enabled: boolean }) =>
      platformFeaturesApi.set(businessId, module, { enabled }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["platform", "features", businessId] }),
  });
}

export function usePlatformToggles(businessId: string | null) {
  return useQuery({
    queryKey: ["platform", "toggles", businessId],
    queryFn: ({ signal }) => platformTogglesApi.list(businessId as string, signal),
    enabled: Boolean(businessId),
    staleTime: 15_000,
  });
}

export function useSetPlatformToggle(businessId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ key, enabled }: { key: string; enabled: boolean }) =>
      platformTogglesApi.set(businessId, key, { enabled }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["platform", "toggles", businessId] }),
  });
}

export function usePlatformSubscription(businessId: string | null) {
  return useQuery({
    queryKey: ["platform", "subscription", businessId],
    queryFn: ({ signal }) => platformSubscriptionApi.get(businessId as string, signal),
    enabled: Boolean(businessId),
    staleTime: 10_000,
  });
}

function useInvalidatePlatformSubscription(businessId: string) {
  const queryClient = useQueryClient();
  return () => void queryClient.invalidateQueries({ queryKey: ["platform", "subscription", businessId] });
}

export function useProvisionSubscription(businessId: string) {
  const invalidate = useInvalidatePlatformSubscription(businessId);
  return useMutation({
    mutationFn: (payload: ProvisionSubscriptionRequest) => platformSubscriptionApi.provision(businessId, payload),
    onSuccess: invalidate,
  });
}

export function useRenewSubscription(businessId: string) {
  const invalidate = useInvalidatePlatformSubscription(businessId);
  return useMutation({
    mutationFn: (payload: RenewSubscriptionRequest) => platformSubscriptionApi.renew(businessId, payload),
    onSuccess: invalidate,
  });
}

export function useSuspendSubscription(businessId: string) {
  const invalidate = useInvalidatePlatformSubscription(businessId);
  return useMutation({
    mutationFn: () => platformSubscriptionApi.suspend(businessId),
    onSuccess: invalidate,
  });
}

export function useCancelSubscription(businessId: string) {
  const invalidate = useInvalidatePlatformSubscription(businessId);
  return useMutation({
    mutationFn: () => platformSubscriptionApi.cancel(businessId),
    onSuccess: invalidate,
  });
}
