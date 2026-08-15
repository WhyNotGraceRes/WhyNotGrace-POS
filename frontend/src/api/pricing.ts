import { apiClient } from "@/api/client";
import type { PriceRuleCreate, PriceRuleOut, PriceRuleUpdate } from "@/types/models";

export const pricingApi = {
  listRules: (params: { item_id?: string } = {}, signal?: AbortSignal) =>
    apiClient.get<PriceRuleOut[]>("/pricing/rules", { params, signal }).then((r) => r.data),

  createRule: (payload: PriceRuleCreate) =>
    apiClient.post<PriceRuleOut>("/pricing/rules", payload).then((r) => r.data),

  updateRule: (ruleId: string, payload: PriceRuleUpdate) =>
    apiClient.put<PriceRuleOut>(`/pricing/rules/${ruleId}`, payload).then((r) => r.data),

  deleteRule: (ruleId: string) => apiClient.delete(`/pricing/rules/${ruleId}`),
};
