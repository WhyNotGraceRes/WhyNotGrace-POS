import { apiClient } from "@/api/client";
import { normalizeKot } from "@/api/normalize";
import type { KOTOut } from "@/types/models";

export const kitchenApi = {
  /** Pending + active KOTs (NEW/ACCEPTED/PREPARING), oldest first — requires ROLE_KITCHEN. */
  queue: (signal?: AbortSignal) =>
    apiClient.get<KOTOut[]>("/kitchen/queue", { signal }).then((r) => r.data.map(normalizeKot)),

  /** KOTs in READY status — requires ROLE_SERVICE (OWNER/MANAGER/SERVICE_COUNTER). */
  ready: (signal?: AbortSignal) =>
    apiClient.get<KOTOut[]>("/kitchen/service/ready", { signal }).then((r) => r.data.map(normalizeKot)),

  /** Requires ROLE_SERVICE on the backend — a pure KITCHEN role must use
   * kotApi.updateStatus instead (ROLE_KITCHEN also permits READY->SERVED there). */
  serve: (kotId: string) =>
    apiClient.post<KOTOut>(`/kitchen/service/${kotId}/serve`).then((r) => normalizeKot(r.data)),
};
