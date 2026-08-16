import { useQuery } from "@tanstack/react-query";
import { subscriptionApi } from "@/api/subscription";

export function useSubscription() {
  return useQuery({
    queryKey: ["subscription"],
    queryFn: ({ signal }) => subscriptionApi.get(signal),
    staleTime: 30_000,
  });
}
