import { apiClient } from "@/api/client";
import type { DashboardResponse } from "@/types/models";

export const dashboardApi = {
  /** OWNER/MANAGER only on the backend (see backend/app/api/dashboard.py
   * ROLE_OPERATIONAL) — do not call this for other roles, they'll get a 403. */
  get: (signal?: AbortSignal) => apiClient.get<DashboardResponse>("/dashboard", { signal }).then((r) => r.data),
};
