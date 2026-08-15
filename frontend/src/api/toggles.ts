import { apiClient } from "@/api/client";
import type { InvoiceSeriesOut, ToggleOut } from "@/types/models";

export const togglesApi = {
  list: (signal?: AbortSignal) =>
    apiClient.get<ToggleOut[]>("/settings/toggles", { signal }).then((r) => r.data),

  update: (key: string, enabled: boolean) =>
    apiClient.put<ToggleOut>(`/settings/toggles/${key}`, { enabled }).then((r) => r.data),

  /** Clears the override so this business follows the default again. */
  reset: (key: string) =>
    apiClient.delete<ToggleOut>(`/settings/toggles/${key}`).then((r) => r.data),

  invoiceSeries: (signal?: AbortSignal) =>
    apiClient.get<InvoiceSeriesOut>("/settings/invoice-series", { signal }).then((r) => r.data),
};
