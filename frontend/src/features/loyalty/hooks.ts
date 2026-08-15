import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { loyaltyApi } from "@/api/loyalty";
import type { LoyaltyRuleCreate, LoyaltyRuleUpdate, RedeemRewardRequest } from "@/types/models";

/** Callers must pass `enabled: false` unless the LOYALTY feature flag is
 * on AND the current role is OWNER/MANAGER (backend: ROLE_OPERATIONAL) —
 * otherwise this is a guaranteed 403/404-behind-flag. A missing loyalty
 * account is a normal 404 (customer just hasn't been enrolled yet), not
 * an error state. */
export function useLoyaltyAccount(customerId: string | null, options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["loyalty", "account", customerId],
    queryFn: ({ signal }) => loyaltyApi.getAccount(customerId as string, signal),
    enabled: Boolean(customerId) && (options.enabled ?? true),
    retry: false,
    staleTime: 30_000,
  });
}

export function useLoyaltyRewards(customerId: string | null, options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["loyalty", "rewards", customerId],
    queryFn: ({ signal }) => loyaltyApi.listRewards(customerId as string, signal),
    enabled: Boolean(customerId) && (options.enabled ?? true),
    staleTime: 30_000,
  });
}

export function useLoyaltyRules(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["loyalty", "rules"],
    queryFn: ({ signal }) => loyaltyApi.listRules(signal),
    enabled: options.enabled ?? true,
    staleTime: 30_000,
  });
}

export function useCreateLoyaltyRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: LoyaltyRuleCreate) => loyaltyApi.createRule(payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["loyalty", "rules"] }),
  });
}

export function useUpdateLoyaltyRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ ruleId, payload }: { ruleId: string; payload: LoyaltyRuleUpdate }) =>
      loyaltyApi.updateRule(ruleId, payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["loyalty", "rules"] }),
  });
}

export function useRedeemReward() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ rewardId, payload }: { rewardId: string; payload: RedeemRewardRequest }) =>
      loyaltyApi.redeemReward(rewardId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["loyalty", "rewards"] });
      void queryClient.invalidateQueries({ queryKey: ["loyalty", "account"] });
    },
  });
}
