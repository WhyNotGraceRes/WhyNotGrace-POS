import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ordersApi } from "@/api/orders";
import type { OrderCreateRequest, OrderSource, OrderStatus } from "@/types/models";

export function useOrders(
  filters: { status_filter?: OrderStatus; source?: OrderSource; active_only?: boolean } = {},
  options: { enabled?: boolean } = {}
) {
  return useQuery({
    queryKey: ["orders", filters],
    queryFn: ({ signal }) => ordersApi.list(filters, signal),
    staleTime: 10_000,
    refetchInterval: 20_000,
    enabled: options.enabled ?? true,
  });
}

export function useOrder(id: string | null) {
  return useQuery({
    queryKey: ["orders", "detail", id],
    queryFn: ({ signal }) => ordersApi.get(id as string, signal),
    enabled: Boolean(id),
  });
}

export function useCreateOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OrderCreateRequest) => ordersApi.create(payload),
    onSuccess: () => {
      // A new order changes table occupancy, the KOT queue, and every
      // order list — invalidate the real backend-derived views that
      // depend on it rather than trying to hand-patch them client-side.
      void queryClient.invalidateQueries({ queryKey: ["orders"] });
      void queryClient.invalidateQueries({ queryKey: ["tables"] });
      void queryClient.invalidateQueries({ queryKey: ["kot"] });
      void queryClient.invalidateQueries({ queryKey: ["kitchen"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useCancelOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => ordersApi.cancel(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["orders"] });
      void queryClient.invalidateQueries({ queryKey: ["kot"] });
      void queryClient.invalidateQueries({ queryKey: ["kitchen"] });
    },
  });
}

function useInvalidateAfterTableMove() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: ["orders"] });
    void queryClient.invalidateQueries({ queryKey: ["tables"] });
    void queryClient.invalidateQueries({ queryKey: ["kot"] });
    void queryClient.invalidateQueries({ queryKey: ["kitchen"] });
    void queryClient.invalidateQueries({ queryKey: ["billing", "unbilled-orders"] });
  };
}

export function useTransferSession() {
  const invalidate = useInvalidateAfterTableMove();
  return useMutation({
    mutationFn: ({ sessionId, locationId }: { sessionId: string; locationId: string }) =>
      ordersApi.transferSession(sessionId, locationId),
    onSuccess: invalidate,
  });
}

export function useMergeSessions() {
  const invalidate = useInvalidateAfterTableMove();
  return useMutation({
    mutationFn: ({ sessionId, intoSessionId }: { sessionId: string; intoSessionId: string }) =>
      ordersApi.mergeSessions(sessionId, intoSessionId),
    onSuccess: invalidate,
  });
}
