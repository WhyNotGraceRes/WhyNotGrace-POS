import { apiClient } from "@/api/client";
import type { SubscriptionOut } from "@/types/models";

/** Read-only — see backend/app/api/subscription.py. Provisioning/renewal
 * is platform-only now (src/api/platform.ts's platformSubscriptionApi). */
export const subscriptionApi = {
  /** Always the honest current state — NOT_CONFIGURED is a real, expected
   * value for a business that has never had a plan set, not an error. */
  get: (signal?: AbortSignal) =>
    apiClient.get<SubscriptionOut>("/subscription", { signal }).then((r) => r.data),
};
