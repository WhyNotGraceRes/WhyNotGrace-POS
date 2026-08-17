import { apiClient } from "@/api/client";
import { normalizeOrder } from "@/api/normalize";
import type { OrderCreateRequest, OrderOut, OrderSource, OrderStatus } from "@/types/models";

export const ordersApi = {
  list: (params: { status_filter?: OrderStatus; source?: OrderSource; active_only?: boolean } = {}, signal?: AbortSignal) =>
    apiClient.get<OrderOut[]>("/orders", { params, signal }).then((r) => r.data.map(normalizeOrder)),

  get: (id: string, signal?: AbortSignal) =>
    apiClient.get<OrderOut>(`/orders/${id}`, { signal }).then((r) => normalizeOrder(r.data)),

  create: (payload: OrderCreateRequest) =>
    apiClient.post<OrderOut>("/orders", payload).then((r) => normalizeOrder(r.data)),

  cancel: (id: string) =>
    apiClient.post<OrderOut>(`/orders/${id}/cancel`).then((r) => normalizeOrder(r.data)),

  /** Moves a session's whole running order to a different, currently-empty
   * table/room. Rejected server-side once a bill exists for the session. */
  transferSession: (sessionId: string, locationId: string) =>
    apiClient
      .post<OrderOut[]>(`/orders/sessions/${sessionId}/transfer`, { location_id: locationId })
      .then((r) => r.data.map(normalizeOrder)),

  /** Folds one open table's orders into another's, for a single combined
   * bill. The losing session is retired for good — see the backend's
   * order_service.merge_sessions docstring. */
  mergeSessions: (sessionId: string, intoSessionId: string) =>
    apiClient
      .post<OrderOut[]>(`/orders/sessions/${sessionId}/merge`, { into_session_id: intoSessionId })
      .then((r) => r.data.map(normalizeOrder)),
};
