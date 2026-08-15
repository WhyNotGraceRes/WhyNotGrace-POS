import { useMutation, useQuery } from "@tanstack/react-query";
import { qrApi } from "@/api/qr";
import type { OrderStatus, QROrderCreateRequest } from "@/types/models";

/** Terminal states — once an order reaches one of these, polling for
 * status updates is pointless and would just waste battery/data. */
const TERMINAL_STATUSES = new Set<OrderStatus>(["SERVED", "DELIVERED", "COMPLETED", "CANCELLED"]);

export function useQrMenu(sessionToken: string | null, lang: string) {
  return useQuery({
    queryKey: ["qr", "menu", sessionToken, lang],
    queryFn: ({ signal }) => qrApi.getMenu(sessionToken as string, lang, signal),
    enabled: Boolean(sessionToken),
    staleTime: 30_000,
  });
}

export function usePlaceQrOrder() {
  return useMutation({
    mutationFn: ({ sessionToken, payload }: { sessionToken: string; payload: QROrderCreateRequest }) =>
      qrApi.placeOrder(sessionToken, payload),
  });
}

export function useQrOrderStatus(sessionToken: string | null, orderId: string | null) {
  return useQuery({
    queryKey: ["qr", "order-status", sessionToken, orderId],
    queryFn: ({ signal }) => qrApi.getOrderStatus(sessionToken as string, orderId as string, signal),
    enabled: Boolean(sessionToken && orderId),
    refetchInterval: (query) => (query.state.data && TERMINAL_STATUSES.has(query.state.data.status) ? false : 6_000),
  });
}
