import { useMutation, useQueryClient } from "@tanstack/react-query";
import { paymentsApi } from "@/api/payments";
import type { CashPaymentRequest, RazorpayOrderCreateRequest, RazorpayVerifyRequest } from "@/types/models";

/** Invalidates the bill (and orders/dashboard, since a paid bill also
 * flips table status and feeds loyalty accrual server-side) after any
 * payment mutation settles, whether it succeeded or failed — a failed
 * attempt can still change nothing, but re-fetching keeps the UI honest
 * rather than trusting client-side optimism. */
function useInvalidateBillingViews() {
  const queryClient = useQueryClient();
  return (billId: string) => {
    void queryClient.invalidateQueries({ queryKey: ["billing", billId] });
    void queryClient.invalidateQueries({ queryKey: ["orders"] });
    void queryClient.invalidateQueries({ queryKey: ["tables"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  };
}

export function useRecordManualPayment() {
  const invalidate = useInvalidateBillingViews();
  return useMutation({
    mutationFn: (payload: CashPaymentRequest) => paymentsApi.recordManual(payload),
    onSuccess: (payment) => invalidate(payment.bill_id),
  });
}

export function useCreateRazorpayOrder() {
  return useMutation({
    mutationFn: ({ payload, idempotencyKey }: { payload: RazorpayOrderCreateRequest; idempotencyKey?: string }) =>
      paymentsApi.createRazorpayOrder(payload, idempotencyKey),
  });
}

export function useVerifyRazorpayPayment() {
  const invalidate = useInvalidateBillingViews();
  return useMutation({
    mutationFn: (payload: RazorpayVerifyRequest) => paymentsApi.verifyRazorpayPayment(payload),
    onSuccess: (payment) => invalidate(payment.bill_id),
  });
}
