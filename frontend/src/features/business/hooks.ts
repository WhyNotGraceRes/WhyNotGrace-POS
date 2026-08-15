import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { businessApi } from "@/api/business";
import type { BusinessUpdateRequest } from "@/types/models";

export function useBusiness() {
  return useQuery({
    queryKey: ["business", "me"],
    queryFn: ({ signal }) => businessApi.getMine(signal),
    staleTime: 5 * 60_000,
  });
}

export function useUpdateBusiness() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: BusinessUpdateRequest) => businessApi.updateMine(payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["business"] }),
  });
}
