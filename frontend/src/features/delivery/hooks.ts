import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { deliveryApi } from "@/api/delivery";
import type { DeliveryStatusUpdateRequest } from "@/types/models";

export function useDeliveryOrders(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["delivery", "orders"],
    queryFn: ({ signal }) => deliveryApi.listOrders(signal),
    staleTime: 10_000,
    refetchInterval: 20_000,
    enabled: options.enabled ?? true,
  });
}

export function useUpdateDeliveryStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ orderId, payload }: { orderId: string; payload: DeliveryStatusUpdateRequest }) =>
      deliveryApi.updateStatus(orderId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["delivery"] });
      void queryClient.invalidateQueries({ queryKey: ["orders"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
