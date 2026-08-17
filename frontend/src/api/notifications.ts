import { apiClient } from "@/api/client";
import type { NotificationListOut } from "@/types/models";

export const notificationsApi = {
  list: (signal?: AbortSignal) =>
    apiClient.get<NotificationListOut>("/notifications", { signal }).then((r) => r.data),

  markRead: (notificationId: string) => apiClient.post(`/notifications/${notificationId}/read`),

  markAllRead: () => apiClient.post("/notifications/read-all"),
};
