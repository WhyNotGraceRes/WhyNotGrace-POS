import { apiClient } from "@/api/client";
import type {
  LoyaltyAccountOut,
  LoyaltyRuleCreate,
  LoyaltyRuleOut,
  LoyaltyRuleUpdate,
  RedeemRewardRequest,
  RewardOut,
} from "@/types/models";

/** Every endpoint here requires the LOYALTY feature flag (enforced by the
 * backend router) — see backend/app/api/loyalty.py. */
export const loyaltyApi = {
  getAccount: (customerId: string, signal?: AbortSignal) =>
    apiClient.get<LoyaltyAccountOut>(`/loyalty/accounts/${customerId}`, { signal }).then((r) => r.data),

  listRewards: (customerId: string, signal?: AbortSignal) =>
    apiClient.get<RewardOut[]>(`/loyalty/accounts/${customerId}/rewards`, { signal }).then((r) => r.data),

  listRules: (signal?: AbortSignal) =>
    apiClient.get<LoyaltyRuleOut[]>("/loyalty/rules", { signal }).then((r) => r.data),

  createRule: (payload: LoyaltyRuleCreate) =>
    apiClient.post<LoyaltyRuleOut>("/loyalty/rules", payload).then((r) => r.data),

  updateRule: (ruleId: string, payload: LoyaltyRuleUpdate) =>
    apiClient.put<LoyaltyRuleOut>(`/loyalty/rules/${ruleId}`, payload).then((r) => r.data),

  redeemReward: (rewardId: string, payload: RedeemRewardRequest) =>
    apiClient.post<RewardOut>(`/loyalty/rewards/${rewardId}/redeem`, payload).then((r) => r.data),
};
