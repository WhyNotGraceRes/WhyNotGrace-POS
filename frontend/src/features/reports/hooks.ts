import { useQuery } from "@tanstack/react-query";
import { reportsApi } from "@/api/reports";
import type { ReportDateRangeParams } from "@/types/models";

export function useSalesReport(params: ReportDateRangeParams & { granularity: "daily" | "weekly" | "monthly" }) {
  return useQuery({
    queryKey: ["reports", "sales", params],
    queryFn: ({ signal }) => reportsApi.sales(params, signal),
    staleTime: 30_000,
  });
}

export function useOrdersReport(params: ReportDateRangeParams) {
  return useQuery({
    queryKey: ["reports", "orders", params],
    queryFn: ({ signal }) => reportsApi.orders(params, signal),
    staleTime: 30_000,
  });
}

export function usePaymentsReport(params: ReportDateRangeParams) {
  return useQuery({
    queryKey: ["reports", "payments", params],
    queryFn: ({ signal }) => reportsApi.payments(params, signal),
    staleTime: 30_000,
  });
}

export function useTopItemsReport(params: ReportDateRangeParams & { limit?: number }) {
  return useQuery({
    queryKey: ["reports", "top-items", params],
    queryFn: ({ signal }) => reportsApi.topItems(params, signal),
    staleTime: 30_000,
  });
}

export function useCategoriesReport(params: ReportDateRangeParams) {
  return useQuery({
    queryKey: ["reports", "categories", params],
    queryFn: ({ signal }) => reportsApi.categories(params, signal),
    staleTime: 30_000,
  });
}

export function useChannelsReport(params: ReportDateRangeParams) {
  return useQuery({
    queryKey: ["reports", "channels", params],
    queryFn: ({ signal }) => reportsApi.channels(params, signal),
    staleTime: 30_000,
  });
}
