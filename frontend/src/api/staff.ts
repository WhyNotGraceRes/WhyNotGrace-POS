import { apiClient } from "@/api/client";
import type { StaffCreateRequest, StaffOut, StaffUpdateRequest } from "@/types/models";

export const staffApi = {
  list: (signal?: AbortSignal) => apiClient.get<StaffOut[]>("/staff", { signal }).then((r) => r.data),

  create: (payload: StaffCreateRequest) => apiClient.post<StaffOut>("/staff", payload).then((r) => r.data),

  update: (staffId: string, payload: StaffUpdateRequest) =>
    apiClient.put<StaffOut>(`/staff/${staffId}`, payload).then((r) => r.data),

  resetAccess: (staffId: string) => apiClient.post<StaffOut>(`/staff/${staffId}/reset-access`).then((r) => r.data),
};
