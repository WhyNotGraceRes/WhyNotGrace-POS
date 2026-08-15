import { apiClient } from "@/api/client";
import type {
  CashPaymentRequest,
  PaymentOut,
  RazorpayOrderCreateRequest,
  RazorpayOrderCreateResponse,
  RazorpayVerifyRequest,
} from "@/types/models";

export const paymentsApi = {
  /** Records a manually-confirmed payment (cash in hand, or a UPI/card
   * payment the staff confirmed through an external terminal) — set
   * `method` accordingly. Marks SUCCESS immediately since a human already
   * verified receipt of funds. */
  recordManual: (payload: CashPaymentRequest) =>
    apiClient.post<PaymentOut>("/payments/cash", payload).then((r) => r.data),

  /** Creates a Razorpay order server-side. Returns 503 if
   * RAZORPAY_KEY_ID/SECRET aren't configured on the backend — callers
   * must surface that plainly, never pretend payment succeeded. */
  createRazorpayOrder: (payload: RazorpayOrderCreateRequest, idempotencyKey?: string) =>
    apiClient
      .post<RazorpayOrderCreateResponse>("/payments/razorpay/order", payload, {
        headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
      })
      .then((r) => r.data),

  verifyRazorpayPayment: (payload: RazorpayVerifyRequest) =>
    apiClient.post<PaymentOut>("/payments/razorpay/verify", payload).then((r) => r.data),
};
