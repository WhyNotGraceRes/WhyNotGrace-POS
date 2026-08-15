import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { kitchenApi } from "@/api/kitchen";

export function useKitchenQueue() {
  return useQuery({
    queryKey: ["kitchen", "queue"],
    queryFn: ({ signal }) => kitchenApi.queue(signal),
    staleTime: 5_000,
    refetchInterval: 15_000,
  });
}

export function useReadyForService(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["kitchen", "ready"],
    queryFn: ({ signal }) => kitchenApi.ready(signal),
    staleTime: 5_000,
    refetchInterval: 15_000,
    enabled: options.enabled ?? true,
  });
}

export function useServeKot() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (kotId: string) => kitchenApi.serve(kotId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["kitchen"] });
      void queryClient.invalidateQueries({ queryKey: ["kot"] });
      void queryClient.invalidateQueries({ queryKey: ["orders"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
