import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/api/admin";

export function useAuditLogs(action?: string) {
  return useQuery({
    queryKey: ["admin", "audit-logs", action ?? "all"],
    queryFn: ({ signal }) => adminApi.listAuditLogs(action ? { action } : {}, signal),
    staleTime: 15_000,
  });
}
