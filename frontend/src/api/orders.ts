import { apiClient } from "@/api/client";
import { normalizeOrder } from "@/api/normalize";
import type { OrderCreateRequest, OrderOut, OrderSource, OrderStatus } from "@/types/models";

export const ordersApi = {
  list: (params: { status_filter?: OrderStatus; source?: OrderSource } = {}, signal?: AbortSignal) =>
    apiClient.get<OrderOut[]>("/orders", { params, signal }).then((r) => r.data.map(normalizeOrder)),

  get: (id: string, signal?: AbortSignal) =>
    apiClient.get<OrderOut>(`/orders/${id}`, { signal }).then((r) => normalizeOrder(r.data)),

  create: (payload: OrderCreateRequest) =>
    apiClient.post<OrderOut>("/orders", payload).then((r) => normalizeOrder(r.data)),

  cancel: (id: string) =>
    apiClient.post<OrderOut>(`/orders/${id}/cancel`).then((r) => normalizeOrder(r.data)),
};
