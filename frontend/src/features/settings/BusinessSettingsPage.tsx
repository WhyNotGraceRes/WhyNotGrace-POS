import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { AlertTriangle } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { parseApiError } from "@/api/errors";
import { useBusiness, useUpdateBusiness } from "@/features/business/hooks";
import { useBusinessSettings, useUpdateBusinessSettings } from "@/features/settings/hooks";
import type { BusinessType } from "@/types/models";

const BUSINESS_TYPES: BusinessType[] = ["RESTAURANT", "HOTEL", "RESORT", "LODGE", "LOUNGE", "CAFE", "CLOUD_KITCHEN", "OTHER"];
const LANGUAGES = ["en", "hi", "mr"];

export function BusinessSettingsPage() {
  const { t } = useTranslation();
  const { data: business, isLoading: businessLoading, isError: businessError } = useBusiness();
  const { data: settings, isLoading: settingsLoading, isError: settingsError } = useBusinessSettings();
  const updateBusiness = useUpdateBusiness();
  const updateSettings = useUpdateBusinessSettings();

  const [name, setName] = useState("");
  const [businessType, setBusinessType] = useState<BusinessType>("RESTAURANT");
  const [defaultLanguage, setDefaultLanguage] = useState("en");
  const [timezone, setTimezone] = useState("");
  const [tax, setTax] = useState("");
  const [serviceCharge, setServiceCharge] = useState("");
  const [currency, setCurrency] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [hydrated, setHydrated] = useState(false);
  if (!hydrated && business && settings) {
    setName(business.name);
    setBusinessType(business.business_type);
    setDefaultLanguage(settings.default_language);
    setTimezone(settings.timezone);
    setTax(String(settings.default_tax_percent));
    setServiceCharge(String(settings.default_service_charge_percent));
    setCurrency(settings.currency);
    setHydrated(true);
  }

  const isLoading = businessLoading || settingsLoading;
  const isError = businessError || settingsError;
  const isPending = updateBusiness.isPending || updateSettings.isPending;

  const handleSave = async () => {
    setError(null);
    try {
      await Promise.all([
        updateBusiness.mutateAsync({ name: name.trim(), business_type: businessType }),
        updateSettings.mutateAsync({
          default_language: defaultLanguage,
          timezone: timezone.trim(),
          default_tax_percent: Number(tax) || 0,
          default_service_charge_percent: Number(serviceCharge) || 0,
          currency: currency.trim(),
        }),
      ]);
      toast.success(t("businessSettings.saved"));
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  return (
    <div>
      <PageHeader title={t("nav.settings")} subtitle={t("businessSettings.subtitle")} />

      {isLoading && (
        <div className="flex justify-center py-16">
          <Spinner className="text-brand-600" />
        </div>
      )}

      {isError && (
        <div className="flex flex-col items-center gap-2 py-16 text-danger-600">
          <AlertTriangle size={22} />
          <p className="text-sm font-medium">{t("businessSettings.loadError")}</p>
        </div>
      )}

      {!isLoading && !isError && (
        <Card className="max-w-xl space-y-4 p-5">
          {error && <p className="rounded-lg border border-danger-500/30 bg-danger-50 px-3 py-2 text-xs text-danger-700">{error}</p>}

          <div>
            <Label htmlFor="biz-name">{t("businessSettings.businessName")}</Label>
            <Input id="biz-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>

          <div>
            <Label htmlFor="biz-type">{t("auth.register.businessType")}</Label>
            <Select id="biz-type" value={businessType} onChange={(e) => setBusinessType(e.target.value as BusinessType)}>
              {BUSINESS_TYPES.map((bt) => (
                <option key={bt} value={bt}>
                  {t(`auth.register.businessTypes.${bt}`)}
                </option>
              ))}
            </Select>
          </div>

          <div>
            <Label htmlFor="biz-lang">{t("businessSettings.defaultLanguage")}</Label>
            <Select id="biz-lang" value={defaultLanguage} onChange={(e) => setDefaultLanguage(e.target.value)}>
              {LANGUAGES.map((lang) => (
                <option key={lang} value={lang}>
                  {t(`businessSettings.language.${lang}`)}
                </option>
              ))}
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="biz-tax">{t("businessSettings.defaultTax")}</Label>
              <Input id="biz-tax" type="number" min={0} max={100} step="0.01" value={tax} onChange={(e) => setTax(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="biz-service">{t("businessSettings.defaultServiceCharge")}</Label>
              <Input id="biz-service" type="number" min={0} max={100} step="0.01" value={serviceCharge} onChange={(e) => setServiceCharge(e.target.value)} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="biz-currency">{t("businessSettings.currency")}</Label>
              <Input id="biz-currency" value={currency} onChange={(e) => setCurrency(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="biz-timezone">{t("businessSettings.timezone")}</Label>
              <Input id="biz-timezone" value={timezone} onChange={(e) => setTimezone(e.target.value)} />
            </div>
          </div>

          <Button isLoading={isPending} onClick={() => void handleSave()}>
            {t("common.save")}
          </Button>
        </Card>
      )}
    </div>
  );
}
