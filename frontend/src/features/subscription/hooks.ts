import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { subscriptionApi } from "@/api/subscription";
import type { SubscriptionVerifyRequest } from "@/types/models";

export function useSubscription() {
  return useQuery({
    queryKey: ["subscription"],
    queryFn: ({ signal }) => subscriptionApi.get(signal),
    staleTime: 30_000,
  });
}

function useInvalidateSubscription() {
  const queryClient = useQueryClient();
  return () => void queryClient.invalidateQueries({ queryKey: ["subscription"] });
}

export function useSubscriptionCheckout() {
  return useMutation({
    mutationFn: () => subscriptionApi.checkout(),
  });
}

export function useVerifySubscriptionPayment() {
  const invalidate = useInvalidateSubscription();
  return useMutation({
    mutationFn: (payload: SubscriptionVerifyRequest) => subscriptionApi.verify(payload),
    onSuccess: invalidate,
  });
}

export function useCancelSubscription() {
  const invalidate = useInvalidateSubscription();
  return useMutation({
    mutationFn: () => subscriptionApi.cancel(),
    onSuccess: invalidate,
  });
}
