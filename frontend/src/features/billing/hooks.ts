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

export function useVoidBillItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ billId, itemId, reason }: { billId: string; itemId: string; reason?: string }) =>
      billingApi.voidItem(billId, itemId, reason),
    onSuccess: (bill) => {
      queryClient.setQueryData(["billing", bill.id], bill);
    },
  });
}

export function useCompBillItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ billId, itemId, reason }: { billId: string; itemId: string; reason?: string }) =>
      billingApi.compItem(billId, itemId, reason),
    onSuccess: (bill) => {
      queryClient.setQueryData(["billing", bill.id], bill);
    },
  });
}

export function useUncompBillItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ billId, itemId }: { billId: string; itemId: string }) =>
      billingApi.uncompItem(billId, itemId),
    onSuccess: (bill) => {
      queryClient.setQueryData(["billing", bill.id], bill);
    },
  });
}

export function useMarkBillNoCharge() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ billId, reason }: { billId: string; reason?: string }) =>
      billingApi.markNoCharge(billId, reason),
    onSuccess: (bill) => {
      queryClient.setQueryData(["billing", bill.id], bill);
      // The table is released when a bill is settled this way, so the floor
      // plan and the open-sessions list are both stale now.
      void queryClient.invalidateQueries({ queryKey: ["orders"] });
      void queryClient.invalidateQueries({ queryKey: ["tables"] });
    },
  });
}
