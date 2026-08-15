import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { kotApi } from "@/api/kot";
import type { KOTStatus, KOTStatusUpdateRequest } from "@/types/models";

export function useKots(filters: { status_filter?: KOTStatus } = {}, options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["kot", filters],
    queryFn: ({ signal }) => kotApi.list(filters, signal),
    staleTime: 5_000,
    refetchInterval: 15_000,
    enabled: options.enabled ?? true,
  });
}

export function useUpdateKotStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: KOTStatusUpdateRequest }) =>
      kotApi.updateStatus(id, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["kot"] });
      void queryClient.invalidateQueries({ queryKey: ["kitchen"] });
      void queryClient.invalidateQueries({ queryKey: ["orders"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
