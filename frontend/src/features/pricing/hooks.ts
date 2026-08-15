import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { pricingApi } from "@/api/pricing";
import type { PriceRuleCreate, PriceRuleUpdate } from "@/types/models";

export function usePriceRules(itemId?: string) {
  return useQuery({
    queryKey: ["pricing-rules", itemId ?? "all"],
    queryFn: ({ signal }) => pricingApi.listRules(itemId ? { item_id: itemId } : {}, signal),
    staleTime: 30_000,
  });
}

function useInvalidatePricing() {
  const queryClient = useQueryClient();
  return () => void queryClient.invalidateQueries({ queryKey: ["pricing-rules"] });
}

export function useCreatePriceRule() {
  const invalidate = useInvalidatePricing();
  return useMutation({
    mutationFn: (payload: PriceRuleCreate) => pricingApi.createRule(payload),
    onSuccess: invalidate,
  });
}

export function useUpdatePriceRule() {
  const invalidate = useInvalidatePricing();
  return useMutation({
    mutationFn: ({ ruleId, payload }: { ruleId: string; payload: PriceRuleUpdate }) =>
      pricingApi.updateRule(ruleId, payload),
    onSuccess: invalidate,
  });
}

export function useDeletePriceRule() {
  const invalidate = useInvalidatePricing();
  return useMutation({
    mutationFn: (ruleId: string) => pricingApi.deleteRule(ruleId),
    onSuccess: invalidate,
  });
}
