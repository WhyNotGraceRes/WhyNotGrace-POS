import { apiClient } from "@/api/client";
import type { BusinessOut, BusinessUpdateRequest } from "@/types/models";

export const businessApi = {
  getMine: (signal?: AbortSignal) =>
    apiClient.get<BusinessOut>("/businesses/me", { signal }).then((r) => r.data),

  updateMine: (payload: BusinessUpdateRequest) =>
    apiClient.put<BusinessOut>("/businesses/me", payload).then((r) => r.data),
};
