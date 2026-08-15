import { apiClient } from "@/api/client";
import type {
  ChargeBandCreate,
  ChargeBandListOut,
  ChargeBandOut,
  ChargeBandUpdate,
  ChargePreviewOut,
  ChargePreviewRequest,
} from "@/types/models";

export const chargesApi = {
  listBands: (signal?: AbortSignal) =>
    apiClient.get<ChargeBandListOut>("/charges/bands", { signal }).then((r) => r.data),

  createBand: (payload: ChargeBandCreate) =>
    apiClient.post<ChargeBandOut>("/charges/bands", payload).then((r) => r.data),

  updateBand: (bandId: string, payload: ChargeBandUpdate) =>
    apiClient.put<ChargeBandOut>(`/charges/bands/${bandId}`, payload).then((r) => r.data),

  deleteBand: (bandId: string) => apiClient.delete<void>(`/charges/bands/${bandId}`).then((r) => r.data),

  preview: (payload: ChargePreviewRequest) =>
    apiClient.post<ChargePreviewOut>("/charges/preview", payload).then((r) => r.data),
};
