import { apiClient } from "@/api/client";
import { normalizeBill } from "@/api/normalize";
import type { ApplyDiscountRequest, BillOut, GenerateBillRequest } from "@/types/models";

export const billingApi = {
  /** Idempotent get-or-create: returns the existing OPEN/PARTIALLY_PAID
   * bill for a session (syncing in any newly added order items), or
   * creates one. There is no separate "list all bills" endpoint on the
   * backend — see BillingPage for how bills are discovered via orders. */
  generate: (payload: GenerateBillRequest) =>
    apiClient.post<BillOut>("/billing/generate", payload).then((r) => normalizeBill(r.data)),

  get: (billId: string, signal?: AbortSignal) =>
    apiClient.get<BillOut>(`/billing/${billId}`, { signal }).then((r) => normalizeBill(r.data)),

  applyDiscount: (billId: string, payload: ApplyDiscountRequest) =>
    apiClient.post<BillOut>(`/billing/${billId}/discount`, payload).then((r) => normalizeBill(r.data)),

  /** Strikes one line off an open bill. Returns the recomputed bill, so the
   * caller never has to work out the new totals itself. */
  voidItem: (billId: string, itemId: string, reason?: string) =>
    apiClient
      .post<BillOut>(`/billing/${billId}/items/${itemId}/void`, { reason })
      .then((r) => normalizeBill(r.data)),
};
