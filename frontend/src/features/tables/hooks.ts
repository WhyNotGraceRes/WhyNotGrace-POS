import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { tablesApi } from "@/api/tables";
import { locationsApi } from "@/api/locations";
import type { LocationCreate, LocationUpdate } from "@/types/models";

export function useTables(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["tables"],
    queryFn: ({ signal }) => tablesApi.list(signal),
    staleTime: 15_000,
    refetchInterval: 30_000,
    enabled: options.enabled ?? true,
  });
}

function useInvalidateTables() {
  const queryClient = useQueryClient();
  return () => void queryClient.invalidateQueries({ queryKey: ["tables"] });
}

export function useCreateTable() {
  const invalidate = useInvalidateTables();
  return useMutation({
    mutationFn: (payload: Omit<LocationCreate, "location_type">) =>
      tablesApi.create({ ...payload, location_type: "TABLE" }),
    onSuccess: invalidate,
  });
}

export function useUpdateTable() {
  const invalidate = useInvalidateTables();
  return useMutation({
    mutationFn: ({ tableId, payload }: { tableId: string; payload: LocationUpdate }) =>
      tablesApi.update(tableId, payload),
    onSuccess: invalidate,
  });
}

export function useDeleteTable() {
  const invalidate = useInvalidateTables();
  return useMutation({
    mutationFn: (tableId: string) => locationsApi.delete(tableId),
    onSuccess: invalidate,
  });
}
