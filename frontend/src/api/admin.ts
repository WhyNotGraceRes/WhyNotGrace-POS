import { apiClient } from "@/api/client";
import type { AuditLogOut } from "@/types/models";

export const adminApi = {
  listAuditLogs: (params: { action?: string; limit?: number } = {}, signal?: AbortSignal) =>
    apiClient.get<AuditLogOut[]>("/admin/audit-logs", { params, signal }).then((r) => r.data),
};
