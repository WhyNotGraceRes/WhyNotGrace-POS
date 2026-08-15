import { apiClient } from "@/api/client";
import type { SubscriptionCheckoutResponse, SubscriptionOut, SubscriptionVerifyRequest } from "@/types/models";

export const subscriptionApi = {
  /** Always the honest current state — NOT_CONFIGURED is a real, expected
   * value for a business that has never subscribed, not an error. */
  get: (signal?: AbortSignal) =>
    apiClient.get<SubscriptionOut>("/subscription", { signal }).then((r) => r.data),

  /** Creates a real Razorpay order server-side for the one ₹699/month
   * plan. Returns 503 if the platform's own Razorpay account isn't
   * configured on the backend — callers must surface that plainly. */
  checkout: () =>
    apiClient.post<SubscriptionCheckoutResponse>("/subscription/checkout").then((r) => r.data),

  verify: (payload: SubscriptionVerifyRequest) =>
    apiClient.post<SubscriptionOut>("/subscription/verify", payload).then((r) => r.data),

  cancel: () => apiClient.post<SubscriptionOut>("/subscription/cancel").then((r) => r.data),
};
