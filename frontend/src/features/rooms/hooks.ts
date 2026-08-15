import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { roomsApi } from "@/api/rooms";
import { locationsApi } from "@/api/locations";
import type { LocationCreate, LocationUpdate } from "@/types/models";

/** GET /rooms requires the HOTEL_ROOMS feature flag at the router level
 * (backend/app/api/rooms.py) — it 403s outright when the flag is off, so
 * callers outside the Rooms page itself (which is already route-gated by
 * the flag) must pass `enabled: false` rather than eating a guaranteed
 * failed request. */
export function useRooms(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["rooms"],
    queryFn: ({ signal }) => roomsApi.list(signal),
    staleTime: 15_000,
    refetchInterval: 30_000,
    enabled: options.enabled ?? true,
  });
}

function useInvalidateRooms() {
  const queryClient = useQueryClient();
  return () => void queryClient.invalidateQueries({ queryKey: ["rooms"] });
}

export function useCreateRoom() {
  const invalidate = useInvalidateRooms();
  return useMutation({
    mutationFn: (payload: Omit<LocationCreate, "location_type">) =>
      roomsApi.create({ ...payload, location_type: "ROOM" }),
    onSuccess: invalidate,
  });
}

export function useUpdateRoom() {
  const invalidate = useInvalidateRooms();
  return useMutation({
    mutationFn: ({ roomId, payload }: { roomId: string; payload: LocationUpdate }) =>
      roomsApi.update(roomId, payload),
    onSuccess: invalidate,
  });
}

export function useDeleteRoom() {
  const invalidate = useInvalidateRooms();
  return useMutation({
    mutationFn: (roomId: string) => locationsApi.delete(roomId),
    onSuccess: invalidate,
  });
}
