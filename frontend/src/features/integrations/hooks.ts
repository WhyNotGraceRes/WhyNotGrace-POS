import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { integrationsApi } from "@/api/integrations";
import type { ConnectCredentialsRequest, IntegrationProvider } from "@/types/models";

export function useIntegrations() {
  return useQuery({
    queryKey: ["integrations"],
    queryFn: ({ signal }) => integrationsApi.list(signal),
    staleTime: 30_000,
  });
}

function useInvalidateIntegrations() {
  const queryClient = useQueryClient();
  return () => void queryClient.invalidateQueries({ queryKey: ["integrations"] });
}

export function useConnectIntegration() {
  const invalidate = useInvalidateIntegrations();
  return useMutation({
    mutationFn: ({ provider, payload }: { provider: IntegrationProvider; payload: ConnectCredentialsRequest }) =>
      integrationsApi.connect(provider, payload),
    onSuccess: invalidate,
  });
}

export function useDisconnectIntegration() {
  const invalidate = useInvalidateIntegrations();
  return useMutation({
    mutationFn: (provider: IntegrationProvider) => integrationsApi.disconnect(provider),
    onSuccess: invalidate,
  });
}

export function useSyncIntegrationMenu() {
  return useMutation({
    mutationFn: (provider: IntegrationProvider) => integrationsApi.syncMenu(provider),
  });
}
