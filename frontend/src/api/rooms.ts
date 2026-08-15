import { apiClient } from "@/api/client";
import type { LocationCreate, LocationOut, LocationUpdate } from "@/types/models";

/** Requires the HOTEL_ROOMS feature flag server-side (see backend
 * app/api/rooms.py router-level dependency). */
export const roomsApi = {
  list: (signal?: AbortSignal) => apiClient.get<LocationOut[]>("/rooms", { signal }).then((r) => r.data),

  create: (payload: LocationCreate) => apiClient.post<LocationOut>("/rooms", payload).then((r) => r.data),

  update: (roomId: string, payload: LocationUpdate) =>
    apiClient.put<LocationOut>(`/rooms/${roomId}`, payload).then((r) => r.data),
};
