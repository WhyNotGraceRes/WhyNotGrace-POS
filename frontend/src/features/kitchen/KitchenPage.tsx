import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { AlertTriangle, ChefHat } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { parseApiError } from "@/api/errors";
import { useKitchenQueue } from "@/features/kitchen/hooks";
import { useUpdateKotStatus } from "@/features/kot/hooks";
import { KotCard } from "@/features/kitchen/components/KotCard";
import type { KOTOut, KOTStatus } from "@/types/models";

export function KitchenPage() {
  const { t } = useTranslation();
  const { data: kots, isLoading, isError, refetch, isFetching } = useKitchenQueue();
  const updateStatus = useUpdateKotStatus();

  const handleAdvance = (kot: KOTOut, next: KOTStatus) => {
    updateStatus.mutate(
      { id: kot.id, payload: { status: next } },
      {
        onError: (err) => toast.error(parseApiError(err).message),
      }
    );
  };

  const handleCancel = (kot: KOTOut) => {
    updateStatus.mutate(
      { id: kot.id, payload: { status: "CANCELLED" } },
      {
        onSuccess: () => toast.success(t("kitchen.kotCancelled")),
        onError: (err) => toast.error(parseApiError(err).message),
      }
    );
  };

  return (
    <div>
      <PageHeader
        title={t("nav.kitchen")}
        subtitle={t("kitchen.subtitle")}
        actions={
          isFetching ? <Spinner size={16} className="text-slate-400" /> : undefined
        }
      />

      {isLoading && (
        <div className="flex justify-center py-16">
          <Spinner className="text-brand-600" />
        </div>
      )}

      {isError && (
        <div className="flex flex-col items-center gap-2 py-16 text-danger-600">
          <AlertTriangle size={22} />
          <p className="text-sm font-medium">{t("kitchen.loadError")}</p>
          <button type="button" onClick={() => void refetch()} className="text-sm font-semibold underline">
            {t("dashboard.retry")}
          </button>
        </div>
      )}

      {!isLoading && !isError && kots && kots.length === 0 && (
        <div className="flex flex-col items-center gap-2 py-16 text-slate-400">
          <ChefHat size={28} />
          <p className="text-sm">{t("kitchen.empty")}</p>
        </div>
      )}

      {!isLoading && !isError && kots && kots.length > 0 && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {kots.map((kot) => (
            <KotCard
              key={kot.id}
              kot={kot}
              onAdvance={handleAdvance}
              onCancel={handleCancel}
              isUpdating={updateStatus.isPending && updateStatus.variables?.id === kot.id}
            />
          ))}
        </div>
      )}
    </div>
  );
}
