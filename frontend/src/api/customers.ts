import { apiClient } from "@/api/client";
import type { CustomerCreate, CustomerOut, CustomerUpdate } from "@/types/models";

export const customersApi = {
  list: (signal?: AbortSignal) => apiClient.get<CustomerOut[]>("/customers", { signal }).then((r) => r.data),

  create: (payload: CustomerCreate) =>
    apiClient.post<CustomerOut>("/customers", payload).then((r) => r.data),

  update: (id: string, payload: CustomerUpdate) =>
    apiClient.put<CustomerOut>(`/customers/${id}`, payload).then((r) => r.data),
};
