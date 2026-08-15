import { apiClient } from "@/api/client";
import type { BusinessSettingsOut, BusinessSettingsUpdateRequest } from "@/types/models";

export const businessSettingsApi = {
  get: (signal?: AbortSignal) => apiClient.get<BusinessSettingsOut>("/settings", { signal }).then((r) => r.data),

  update: (payload: BusinessSettingsUpdateRequest) =>
    apiClient.put<BusinessSettingsOut>("/settings", payload).then((r) => r.data),
};
