import { apiClient } from "@/api/client";
import type { LocationCreate, LocationOut, LocationUpdate } from "@/types/models";

/** Generic location CRUD — used by the Tables/Rooms admin UI for delete,
 * since /tables and /rooms only expose create/update (see backend
 * app/api/tables.py, app/api/rooms.py — no DELETE there). */
export const locationsApi = {
  list: (params: { location_type?: string } = {}, signal?: AbortSignal) =>
    apiClient.get<LocationOut[]>("/locations", { params, signal }).then((r) => r.data),

  create: (payload: LocationCreate) =>
    apiClient.post<LocationOut>("/locations", payload).then((r) => r.data),

  update: (locationId: string, payload: LocationUpdate) =>
    apiClient.put<LocationOut>(`/locations/${locationId}`, payload).then((r) => r.data),

  delete: (locationId: string) => apiClient.delete(`/locations/${locationId}`),
};
