import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { customersApi } from "@/api/customers";
import type { CustomerCreate, CustomerUpdate } from "@/types/models";

export function useCustomers() {
  return useQuery({
    queryKey: ["customers"],
    queryFn: ({ signal }) => customersApi.list(signal),
    staleTime: 30_000,
  });
}

export function useCreateCustomer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CustomerCreate) => customersApi.create(payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["customers"] }),
  });
}

export function useUpdateCustomer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: CustomerUpdate }) => customersApi.update(id, payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["customers"] }),
  });
}
