import { apiClient } from "@/api/client";
import type { LocationCreate, LocationOut, LocationUpdate } from "@/types/models";

export const tablesApi = {
  list: (signal?: AbortSignal) => apiClient.get<LocationOut[]>("/tables", { signal }).then((r) => r.data),

  create: (payload: LocationCreate) => apiClient.post<LocationOut>("/tables", payload).then((r) => r.data),

  update: (tableId: string, payload: LocationUpdate) =>
    apiClient.put<LocationOut>(`/tables/${tableId}`, payload).then((r) => r.data),
};
