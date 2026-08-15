import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";

import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { parseApiError } from "@/api/errors";
import { useConnectIntegration } from "@/features/integrations/hooks";
import type { IntegrationProvider } from "@/types/models";

const FIELDS_BY_PROVIDER: Record<IntegrationProvider, { key: string; labelKey: string; optional?: boolean }[]> = {
  RAZORPAY: [
    { key: "key_id", labelKey: "integrationsAdmin.keyId" },
    { key: "key_secret", labelKey: "integrationsAdmin.keySecret" },
    { key: "webhook_secret", labelKey: "integrationsAdmin.webhookSecret", optional: true },
  ],
  ZOMATO: [
    { key: "client_id", labelKey: "integrationsAdmin.clientId" },
    { key: "client_secret", labelKey: "integrationsAdmin.clientSecret" },
  ],
  SWIGGY: [
    { key: "client_id", labelKey: "integrationsAdmin.clientId" },
    { key: "client_secret", labelKey: "integrationsAdmin.clientSecret" },
  ],
};

export function ConnectDialog({
  open,
  provider,
  onClose,
}: {
  open: boolean;
  provider: IntegrationProvider | null;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const connect = useConnectIntegration();
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  if (!provider) return null;
  const fields = FIELDS_BY_PROVIDER[provider];

  const handleSubmit = async () => {
    setError(null);
    if (fields.some((f) => !f.optional && !values[f.key]?.trim())) {
      setError(t("integrationsAdmin.fieldsRequired"));
      return;
    }
    try {
      const credentials = Object.fromEntries(
        Object.entries(values).filter(([, v]) => v.trim().length > 0)
      );
      await connect.mutateAsync({ provider, payload: { credentials } });
      toast.success(t("integrationsAdmin.connected", { provider: t(`integrationsAdmin.provider.${provider}`) }));
      setValues({});
      onClose();
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title={t("integrationsAdmin.connectTitle", { provider: t(`integrationsAdmin.provider.${provider}`) })} size="sm">
      <div className="space-y-3">
        {provider === "RAZORPAY" && (
          <p className="rounded-lg border border-warning-300 bg-warning-50 px-3 py-2 text-xs text-warning-800">
            {t("integrationsAdmin.razorpayNote")}
          </p>
        )}
        {error && <p className="text-xs text-danger-600">{error}</p>}
        {fields.map((field) => (
          <div key={field.key}>
            <Label htmlFor={`cred-${field.key}`}>{t(field.labelKey)}</Label>
            <Input
              id={`cred-${field.key}`}
              type="password"
              value={values[field.key] ?? ""}
              onChange={(e) => setValues((prev) => ({ ...prev, [field.key]: e.target.value }))}
            />
          </div>
        ))}
        <Button className="w-full" isLoading={connect.isPending} onClick={() => void handleSubmit()}>
          {t("integrationsAdmin.connect")}
        </Button>
      </div>
    </Dialog>
  );
}
