import { useState } from "react";
import { useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { AlertTriangle, Ban, CheckCircle2 } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import { Switch } from "@/components/ui/Switch";
import { parseApiError } from "@/api/errors";
import {
  usePlatformBusiness,
  usePlatformFeatures,
  usePlatformSubscription,
  usePlatformToggles,
  useSetBusinessActive,
  useSetPlatformFeature,
  useSetPlatformToggle,
} from "@/features/platform/hooks";
import { SubscriptionPanel } from "@/features/platform/components/SubscriptionPanel";

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
}

export function BusinessDetailPage() {
  const { businessId } = useParams<{ businessId: string }>();
  const id = businessId ?? null;

  const { data: business, isLoading, isError } = usePlatformBusiness(id);
  const { data: features } = usePlatformFeatures(id);
  const { data: toggleRows } = usePlatformToggles(id);
  const { data: subscription } = usePlatformSubscription(id);

  const setActive = useSetBusinessActive();
  const setFeature = useSetPlatformFeature(id ?? "");
  const setToggle = useSetPlatformToggle(id ?? "");

  const [pendingModule, setPendingModule] = useState<string | null>(null);
  const [pendingToggle, setPendingToggle] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner className="text-brand-600" />
      </div>
    );
  }

  if (isError || !business || !id) {
    return (
      <div className="flex flex-col items-center gap-2 py-16 text-danger-600">
        <AlertTriangle size={22} />
        <p className="text-sm font-medium">Couldn't load this business.</p>
      </div>
    );
  }

  const handleToggleActive = async () => {
    const next = !business.is_active;
    if (!window.confirm(next ? "Reactivate this business?" : "Suspend this business immediately? Dashboard login and public ordering both stop working.")) return;
    try {
      await setActive.mutateAsync({ businessId: id, isActive: next });
      toast.success(next ? "Business reactivated." : "Business suspended.");
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  const handleToggleFeature = async (module: string, enabled: boolean) => {
    setPendingModule(module);
    try {
      await setFeature.mutateAsync({ module: module as never, enabled });
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setPendingModule(null);
    }
  };

  const handleToggleSetting = async (key: string, enabled: boolean) => {
    setPendingToggle(key);
    try {
      await setToggle.mutateAsync({ key, enabled });
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setPendingToggle(null);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={business.name}
        subtitle={`${business.business_type.replace(/_/g, " ")} · ${business.slug} · provisioned ${formatDate(business.created_at)}`}
        actions={
          <Button
            variant={business.is_active ? "danger" : "primary"}
            isLoading={setActive.isPending}
            onClick={() => void handleToggleActive()}
          >
            {business.is_active ? <Ban size={16} /> : <CheckCircle2 size={16} />}
            {business.is_active ? "Suspend business" : "Reactivate business"}
          </Button>
        }
      />

      <Card className="p-5">
        <h2 className="mb-1 text-sm font-bold text-slate-800">Subscription</h2>
        <p className="mb-4 text-xs text-slate-500">
          What this business is being charged and whether its plan is current.
        </p>
        <SubscriptionPanel businessId={id} subscription={subscription} />
      </Card>

      <Card className="p-5">
        <h2 className="mb-1 text-sm font-bold text-slate-800">Modules</h2>
        <p className="mb-4 text-xs text-slate-500">
          What this business can use. CORE_POS can never be turned off.
        </p>
        <div className="divide-y divide-slate-100">
          {(features ?? []).map((flag) => (
            <div key={flag.module} className="flex items-center justify-between gap-4 py-2.5">
              <span className="text-sm text-slate-700">{flag.module.replace(/_/g, " ")}</span>
              <Switch
                checked={flag.enabled}
                disabled={flag.module === "CORE_POS" || pendingModule === flag.module}
                onChange={(checked) => void handleToggleFeature(flag.module, checked)}
                label={flag.module}
              />
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-5">
        <h2 className="mb-1 text-sm font-bold text-slate-800">Entitlement toggles</h2>
        <p className="mb-4 text-xs text-slate-500">
          Fine-grained switches this business cannot change itself — see each one's description.
        </p>
        <div className="divide-y divide-slate-100">
          {(toggleRows ?? [])
            .filter((row) => !row.owner_editable)
            .map((row) => (
              <div key={row.key} className="flex items-center justify-between gap-4 py-2.5">
                <div>
                  <p className="text-sm text-slate-700">{row.label}</p>
                  <p className="text-xs text-slate-500">{row.description}</p>
                </div>
                <Switch
                  checked={row.enabled}
                  disabled={pendingToggle === row.key}
                  onChange={(checked) => void handleToggleSetting(row.key, checked)}
                  label={row.label}
                />
              </div>
            ))}
          {(toggleRows ?? []).every((row) => row.owner_editable) && (
            <p className="py-2.5 text-xs text-slate-500">
              No entitlement-class toggles registered yet — every switch shipped so far is owner-editable.
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}
