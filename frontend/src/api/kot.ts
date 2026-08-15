import { apiClient } from "@/api/client";
import { normalizeKot } from "@/api/normalize";
import type { KOTOut, KOTStatus, KOTStatusUpdateRequest } from "@/types/models";

export const kotApi = {
  list: (params: { status_filter?: KOTStatus } = {}, signal?: AbortSignal) =>
    apiClient.get<KOTOut[]>("/kot", { params, signal }).then((r) => r.data.map(normalizeKot)),

  get: (id: string, signal?: AbortSignal) =>
    apiClient.get<KOTOut>(`/kot/${id}`, { signal }).then((r) => normalizeKot(r.data)),

  updateStatus: (id: string, payload: KOTStatusUpdateRequest) =>
    apiClient.put<KOTOut>(`/kot/${id}/status`, payload).then((r) => normalizeKot(r.data)),
};
