import { apiClient } from "@/api/client";
import type {
  CategoryPerformanceReportRow,
  ChannelPerformanceReportRow,
  OrderCountReportRow,
  PaymentBreakdownReportRow,
  ReportDateRangeParams,
  SalesReportRow,
  TopItemReportRow,
} from "@/types/models";

export const reportsApi = {
  sales: (params: ReportDateRangeParams & { granularity?: "daily" | "weekly" | "monthly" }, signal?: AbortSignal) =>
    apiClient.get<SalesReportRow[]>("/reports/sales", { params, signal }).then((r) => r.data),

  orders: (params: ReportDateRangeParams, signal?: AbortSignal) =>
    apiClient.get<OrderCountReportRow[]>("/reports/orders", { params, signal }).then((r) => r.data),

  payments: (params: ReportDateRangeParams, signal?: AbortSignal) =>
    apiClient.get<PaymentBreakdownReportRow[]>("/reports/payments", { params, signal }).then((r) => r.data),

  topItems: (params: ReportDateRangeParams & { limit?: number }, signal?: AbortSignal) =>
    apiClient.get<TopItemReportRow[]>("/reports/top-items", { params, signal }).then((r) => r.data),

  categories: (params: ReportDateRangeParams, signal?: AbortSignal) =>
    apiClient.get<CategoryPerformanceReportRow[]>("/reports/categories", { params, signal }).then((r) => r.data),

  channels: (params: ReportDateRangeParams, signal?: AbortSignal) =>
    apiClient.get<ChannelPerformanceReportRow[]>("/reports/channels", { params, signal }).then((r) => r.data),
};
