import { apiClient } from "@/api/client";
import type { CloseShiftRequest, ShiftOut, ShiftReportOut } from "@/types/models";

export const shiftsApi = {
  /** This user's own open drawer, or null. */
  current: (signal?: AbortSignal) =>
    apiClient.get<ShiftOut | null>("/shifts/current", { signal }).then((r) => r.data),

  open: (openingFloat: number) =>
    apiClient.post<ShiftOut>("/shifts", { opening_float: openingFloat }).then((r) => r.data),

  close: (shiftId: string, payload: CloseShiftRequest) =>
    apiClient.post<ShiftReportOut>(`/shifts/${shiftId}/close`, payload).then((r) => r.data),

  report: (shiftId: string, signal?: AbortSignal) =>
    apiClient.get<ShiftReportOut>(`/shifts/${shiftId}/report`, { signal }).then((r) => r.data),

  list: (signal?: AbortSignal) =>
    apiClient.get<ShiftOut[]>("/shifts", { signal }).then((r) => r.data),
};
