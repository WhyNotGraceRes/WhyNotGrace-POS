import { apiClient } from "@/api/client";
import { normalizeBill, normalizeOrder } from "@/api/normalize";
import type { ApplyDiscountRequest, BillOut, GenerateBillRequest, OrderOut } from "@/types/models";

export const billingApi = {
  /** Idempotent get-or-create: returns the existing OPEN/PARTIALLY_PAID
   * bill for a session (syncing in any newly added order items), or
   * creates one. There is no separate "list all bills" endpoint on the
   * backend — see BillingPage for how bills are discovered via orders. */
  generate: (payload: GenerateBillRequest) =>
    apiClient.post<BillOut>("/billing/generate", payload).then((r) => normalizeBill(r.data)),

  /** Orders with no money settled against them yet — what the Billing page
   * groups into sessions. Not the same as GET /orders: a session's history
   * can span settled AND unsettled visits (see backend's
   * billing_service.list_unbilled_orders), so this scopes correctly where
   * a raw order list can't. */
  unbilledOrders: (signal?: AbortSignal) =>
    apiClient.get<OrderOut[]>("/billing/unbilled-orders", { signal }).then((r) => r.data.map(normalizeOrder)),

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

  /** Gives one line away. It stays on the bill, marked NC. */
  compItem: (billId: string, itemId: string, reason?: string) =>
    apiClient
      .post<BillOut>(`/billing/${billId}/items/${itemId}/comp`, { reason })
      .then((r) => normalizeBill(r.data)),

  /** Charges for a comped line again. There is no void equivalent, by design. */
  uncompItem: (billId: string, itemId: string) =>
    apiClient
      .post<BillOut>(`/billing/${billId}/items/${itemId}/uncomp`, {})
      .then((r) => normalizeBill(r.data)),

  markNoCharge: (billId: string, reason?: string) =>
    apiClient.post<BillOut>(`/billing/${billId}/no-charge`, { reason }).then((r) => normalizeBill(r.data)),

  /** Cancels the whole bill — paid or not. The server frees the table and
   * (for a paid bill) leaves the payment rows in place as a record; this
   * does not refund money, it only marks the invoice cancelled. */
  voidBill: (billId: string, reason?: string) =>
    apiClient.post<BillOut>(`/billing/${billId}/void`, { reason }).then((r) => normalizeBill(r.data)),
};
