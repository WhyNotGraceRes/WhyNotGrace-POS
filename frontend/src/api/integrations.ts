import { apiClient } from "@/api/client";
import type { ConnectCredentialsRequest, IntegrationOut, IntegrationProvider } from "@/types/models";

export const integrationsApi = {
  list: (signal?: AbortSignal) => apiClient.get<IntegrationOut[]>("/integrations", { signal }).then((r) => r.data),

  connect: (provider: IntegrationProvider, payload: ConnectCredentialsRequest) =>
    apiClient.put<IntegrationOut>(`/integrations/${provider}/credentials`, payload).then((r) => r.data),

  disconnect: (provider: IntegrationProvider) =>
    apiClient.delete<IntegrationOut>(`/integrations/${provider}/credentials`).then((r) => r.data),

  syncMenu: (provider: IntegrationProvider) =>
    apiClient.post(`/integrations/${provider}/menu-sync`).then((r) => r.data),
};
