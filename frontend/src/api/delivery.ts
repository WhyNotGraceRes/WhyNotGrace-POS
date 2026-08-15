import { apiClient } from "@/api/client";
import { normalizeOrder } from "@/api/normalize";
import type { DeliveryStatusUpdateRequest, OrderOut } from "@/types/models";

/** Requires the DELIVERY feature flag + ROLE_DELIVERY server-side (see
 * backend/app/api/delivery.py). Status transitions are re-validated
 * server-side (see order_service.DELIVERY_STATUS_TRANSITIONS) — an
 * illegal transition is rejected with 400 even if the UI never offers it. */
export const deliveryApi = {
  listOrders: (signal?: AbortSignal) =>
    apiClient.get<OrderOut[]>("/delivery/orders", { signal }).then((r) => r.data.map(normalizeOrder)),

  updateStatus: (orderId: string, payload: DeliveryStatusUpdateRequest) =>
    apiClient.put<OrderOut>(`/delivery/orders/${orderId}/status`, payload).then((r) => normalizeOrder(r.data)),
};
