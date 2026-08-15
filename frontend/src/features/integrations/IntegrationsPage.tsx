import { useState } from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle, Link2, RefreshCw, Unlink } from "lucide-react";
import toast from "react-hot-toast";

import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import { parseApiError } from "@/api/errors";
import { useIsFeatureEnabled } from "@/features/settings/hooks";
import { useDisconnectIntegration, useIntegrations, useSyncIntegrationMenu } from "@/features/integrations/hooks";
import { ConnectDialog } from "@/features/integrations/components/ConnectDialog";
import type { IntegrationProvider } from "@/types/models";

const SYNCABLE: Record<IntegrationProvider, boolean> = { RAZORPAY: false, ZOMATO: true, SWIGGY: true };

export function IntegrationsPage() {
  const { t } = useTranslation();
  const { data: integrations, isLoading, isError } = useIntegrations();
  const disconnect = useDisconnectIntegration();
  const syncMenu = useSyncIntegrationMenu();
  const zomatoEnabled = useIsFeatureEnabled("ZOMATO");
  const swiggyEnabled = useIsFeatureEnabled("SWIGGY");
  const razorpayEnabled = useIsFeatureEnabled("ONLINE_PAYMENT");
  const [connectProvider, setConnectProvider] = useState<IntegrationProvider | null>(null);

  const featureEnabledFor = (provider: IntegrationProvider) =>
    provider === "ZOMATO" ? zomatoEnabled : provider === "SWIGGY" ? swiggyEnabled : provider === "RAZORPAY" ? razorpayEnabled : true;

  const handleDisconnect = async (provider: IntegrationProvider) => {
    if (!window.confirm(t("integrationsAdmin.confirmDisconnect", { provider: t(`integrationsAdmin.provider.${provider}`) }))) return;
    try {
      await disconnect.mutateAsync(provider);
      toast.success(t("integrationsAdmin.disconnected"));
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  const handleSync = async (provider: IntegrationProvider) => {
    try {
      await syncMenu.mutateAsync(provider);
      toast.success(t("integrationsAdmin.syncRequested"));
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  return (
    <div>
      <PageHeader title={t("nav.integrations")} subtitle={t("integrationsAdmin.subtitle")} />

      {isLoading && (
        <div className="flex justify-center py-16">
          <Spinner className="text-brand-600" />
        </div>
      )}

      {isError && (
        <div className="flex flex-col items-center gap-2 py-16 text-danger-600">
          <AlertTriangle size={22} />
          <p className="text-sm font-medium">{t("integrationsAdmin.loadError")}</p>
        </div>
      )}

      {!isLoading && !isError && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {(integrations ?? []).map((integration) => (
            <Card key={integration.provider} className="p-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-bold text-slate-900">{t(`integrationsAdmin.provider.${integration.provider}`)}</p>
                  {integration.is_connected ? (
                    <span className="mt-1 inline-block rounded-full bg-success-50 px-2 py-0.5 text-xs font-semibold text-success-700">
                      {t("integrationsAdmin.connectedStatus")}
                    </span>
                  ) : (
                    <span className="mt-1 inline-block rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-500">
                      {t("integrationsAdmin.notConnected")}
                    </span>
                  )}
                  <span
                    className={cn(
                      "ml-1.5 mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-semibold",
                      featureEnabledFor(integration.provider)
                        ? "bg-brand-50 text-brand-700"
                        : "bg-slate-100 text-slate-500"
                    )}
                  >
                    {featureEnabledFor(integration.provider) ? t("integrationsAdmin.featureEnabled") : t("integrationsAdmin.featureDisabled")}
                  </span>
                  {integration.is_connected && integration.masked_key_id && (
                    <p className="mt-1.5 font-mono text-xs text-slate-500">{integration.masked_key_id}</p>
                  )}
                  {!featureEnabledFor(integration.provider) && (
                    <p className="mt-1.5 text-xs text-warning-700">{t("integrationsAdmin.featureDisabledHint")}</p>
                  )}
                </div>
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                {integration.is_connected ? (
                  <Button variant="secondary" size="sm" onClick={() => void handleDisconnect(integration.provider)}>
                    <Unlink size={13} />
                    {t("integrationsAdmin.disconnect")}
                  </Button>
                ) : (
                  <Button size="sm" onClick={() => setConnectProvider(integration.provider)}>
                    <Link2 size={13} />
                    {t("integrationsAdmin.connect")}
                  </Button>
                )}
                {SYNCABLE[integration.provider] && integration.is_connected && featureEnabledFor(integration.provider) && (
                  <Button variant="secondary" size="sm" isLoading={syncMenu.isPending} onClick={() => void handleSync(integration.provider)}>
                    <RefreshCw size={13} />
                    {t("integrationsAdmin.syncMenu")}
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      <ConnectDialog open={Boolean(connectProvider)} provider={connectProvider} onClose={() => setConnectProvider(null)} />
    </div>
  );
}
