import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { billingApi } from "@/api/billing";
import type { ApplyDiscountRequest, GenerateBillRequest } from "@/types/models";

export function useBill(billId: string | null) {
  return useQuery({
    queryKey: ["billing", billId],
    queryFn: ({ signal }) => billingApi.get(billId as string, signal),
    enabled: Boolean(billId),
    staleTime: 5_000,
  });
}

export function useGenerateBill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: GenerateBillRequest) => billingApi.generate(payload),
    onSuccess: (bill) => {
      queryClient.setQueryData(["billing", bill.id], bill);
      void queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });
}

export function useApplyDiscount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ billId, payload }: { billId: string; payload: ApplyDiscountRequest }) =>
      billingApi.applyDiscount(billId, payload),
    onSuccess: (bill) => {
      queryClient.setQueryData(["billing", bill.id], bill);
    },
  });
}
