import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle, BarChart3 } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { Spinner } from "@/components/ui/Spinner";
import { formatCurrency, formatNumber } from "@/lib/format";
import {
  useCategoriesReport,
  useChannelsReport,
  useOrdersReport,
  usePaymentsReport,
  useSalesReport,
  useTopItemsReport,
} from "@/features/reports/hooks";

function ReportSection<T>({
  title,
  isLoading,
  isError,
  rows,
  children,
}: {
  title: string;
  isLoading: boolean;
  isError: boolean;
  rows: T[] | undefined;
  children: (rows: T[]) => React.ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <Card className="p-4">
      <p className="mb-3 text-sm font-bold text-stone-900">{title}</p>
      {isLoading && (
        <div className="flex justify-center py-8">
          <Spinner className="text-brand-600" />
        </div>
      )}
      {isError && (
        <div className="flex flex-col items-center gap-1.5 py-8 text-danger-600">
          <AlertTriangle size={18} />
          <p className="text-xs font-medium">{t("reports.loadError")}</p>
        </div>
      )}
      {!isLoading && !isError && (!rows || rows.length === 0) && (
        <p className="py-8 text-center text-xs text-stone-400">{t("reports.empty")}</p>
      )}
      {!isLoading && !isError && rows && rows.length > 0 && children(rows)}
    </Card>
  );
}

export function ReportsPage() {
  const { t } = useTranslation();
  const today = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const thirtyDaysAgo = useMemo(() => new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10), []);

  const [startDate, setStartDate] = useState(thirtyDaysAgo);
  const [endDate, setEndDate] = useState(today);
  const [granularity, setGranularity] = useState<"daily" | "weekly" | "monthly">("daily");

  const params = { start_date: startDate || undefined, end_date: endDate || undefined };

  const sales = useSalesReport({ ...params, granularity });
  const orders = useOrdersReport(params);
  const payments = usePaymentsReport(params);
  const topItems = useTopItemsReport({ ...params, limit: 10 });
  const categories = useCategoriesReport(params);
  const channels = useChannelsReport(params);

  const salesTotal = (sales.data ?? []).reduce((sum, r) => sum + r.total_sales, 0);
  const ordersTotal = (orders.data ?? []).reduce((sum, r) => sum + r.order_count, 0);
  const avgOrderValue = ordersTotal > 0 ? salesTotal / ordersTotal : 0;

  return (
    <div>
      <PageHeader title={t("nav.reports")} subtitle={t("reports.subtitle")} />

      <Card className="mb-4 p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <Label htmlFor="report-start">{t("reports.startDate")}</Label>
            <Input id="report-start" type="date" value={startDate} max={endDate} onChange={(e) => setStartDate(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="report-end">{t("reports.endDate")}</Label>
            <Input id="report-end" type="date" value={endDate} min={startDate} max={today} onChange={(e) => setEndDate(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="report-granularity">{t("reports.granularity")}</Label>
            <Select id="report-granularity" value={granularity} onChange={(e) => setGranularity(e.target.value as typeof granularity)}>
              <option value="daily">{t("reports.daily")}</option>
              <option value="weekly">{t("reports.weekly")}</option>
              <option value="monthly">{t("reports.monthly")}</option>
            </Select>
          </div>
        </div>
      </Card>

      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Card className="p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">{t("reports.totalSales")}</p>
          <p className="mt-1 text-xl font-bold text-stone-900">
            {sales.isLoading ? <Spinner className="text-brand-600" size={16} /> : formatCurrency(salesTotal)}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">{t("reports.totalOrders")}</p>
          <p className="mt-1 text-xl font-bold text-stone-900">
            {orders.isLoading ? <Spinner className="text-brand-600" size={16} /> : formatNumber(ordersTotal)}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">{t("reports.avgOrderValue")}</p>
          <p className="mt-1 text-xl font-bold text-stone-900">
            {sales.isLoading || orders.isLoading ? <Spinner className="text-brand-600" size={16} /> : formatCurrency(avgOrderValue)}
          </p>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ReportSection title={t("reports.salesOverTime")} isLoading={sales.isLoading} isError={sales.isError} rows={sales.data}>
          {(rows) => (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-stone-400">
                  <th className="pb-1.5 font-medium">{t("reports.period")}</th>
                  <th className="pb-1.5 text-right font-medium">{t("reports.sales")}</th>
                  <th className="pb-1.5 text-right font-medium">{t("reports.billsPaid")}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.period} className="border-t border-stone-100">
                    <td className="py-1.5 text-stone-700">{new Date(r.period).toLocaleDateString()}</td>
                    <td className="py-1.5 text-right font-medium text-stone-900">{formatCurrency(r.total_sales)}</td>
                    <td className="py-1.5 text-right text-stone-600">{formatNumber(r.bills_paid)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </ReportSection>

        <ReportSection title={t("reports.ordersBySource")} isLoading={orders.isLoading} isError={orders.isError} rows={orders.data}>
          {(rows) => (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-stone-400">
                  <th className="pb-1.5 font-medium">{t("reports.source")}</th>
                  <th className="pb-1.5 text-right font-medium">{t("reports.orderCount")}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.source} className="border-t border-stone-100">
                    <td className="py-1.5 text-stone-700">{t(`orderSource.${r.source}`, r.source)}</td>
                    <td className="py-1.5 text-right font-medium text-stone-900">{formatNumber(r.order_count)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </ReportSection>

        <ReportSection title={t("reports.paymentBreakdown")} isLoading={payments.isLoading} isError={payments.isError} rows={payments.data}>
          {(rows) => (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-stone-400">
                  <th className="pb-1.5 font-medium">{t("reports.method")}</th>
                  <th className="pb-1.5 text-right font-medium">{t("reports.count")}</th>
                  <th className="pb-1.5 text-right font-medium">{t("reports.amount")}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.method} className="border-t border-stone-100">
                    <td className="py-1.5 text-stone-700">{t(`paymentMethod.${r.method}`, r.method)}</td>
                    <td className="py-1.5 text-right text-stone-600">{formatNumber(r.count)}</td>
                    <td className="py-1.5 text-right font-medium text-stone-900">{formatCurrency(r.total_amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </ReportSection>

        <ReportSection title={t("reports.topItems")} isLoading={topItems.isLoading} isError={topItems.isError} rows={topItems.data}>
          {(rows) => (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-stone-400">
                  <th className="pb-1.5 font-medium">{t("reports.item")}</th>
                  <th className="pb-1.5 text-right font-medium">{t("reports.quantitySold")}</th>
                  <th className="pb-1.5 text-right font-medium">{t("reports.revenue")}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.menu_item_id} className="border-t border-stone-100">
                    <td className="py-1.5 text-stone-700">{r.name}</td>
                    <td className="py-1.5 text-right text-stone-600">{formatNumber(r.quantity_sold)}</td>
                    <td className="py-1.5 text-right font-medium text-stone-900">{formatCurrency(r.revenue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </ReportSection>

        <ReportSection title={t("reports.categoryPerformance")} isLoading={categories.isLoading} isError={categories.isError} rows={categories.data}>
          {(rows) => (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-stone-400">
                  <th className="pb-1.5 font-medium">{t("reports.category")}</th>
                  <th className="pb-1.5 text-right font-medium">{t("reports.revenue")}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.category_id} className="border-t border-stone-100">
                    <td className="py-1.5 text-stone-700">{r.category_name}</td>
                    <td className="py-1.5 text-right font-medium text-stone-900">{formatCurrency(r.revenue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </ReportSection>

        <ReportSection title={t("reports.channelPerformance")} isLoading={channels.isLoading} isError={channels.isError} rows={channels.data}>
          {(rows) => (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-stone-400">
                  <th className="pb-1.5 font-medium">{t("reports.channel")}</th>
                  <th className="pb-1.5 text-right font-medium">{t("reports.orderCount")}</th>
                  <th className="pb-1.5 text-right font-medium">{t("reports.revenue")}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.channel} className="border-t border-stone-100">
                    <td className="py-1.5 text-stone-700">{t(`orderSource.${r.channel}`, r.channel)}</td>
                    <td className="py-1.5 text-right text-stone-600">{formatNumber(r.order_count)}</td>
                    <td className="py-1.5 text-right font-medium text-stone-900">{formatCurrency(r.revenue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </ReportSection>
      </div>

      {!sales.isLoading &&
        !orders.isLoading &&
        !payments.isLoading &&
        !topItems.isLoading &&
        !categories.isLoading &&
        !channels.isLoading &&
        (sales.data ?? []).length === 0 &&
        (orders.data ?? []).length === 0 &&
        (payments.data ?? []).length === 0 && (
          <div className="mt-4 flex flex-col items-center gap-2 py-10 text-center text-stone-400">
            <BarChart3 size={22} />
            <p className="text-sm">{t("reports.noDataForRange")}</p>
          </div>
        )}
    </div>
  );
}
