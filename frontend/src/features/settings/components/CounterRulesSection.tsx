import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { AlertTriangle, Lock, RotateCcw } from "lucide-react";

import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { Switch } from "@/components/ui/Switch";
import { parseApiError } from "@/api/errors";
import {
  useInvoiceSeries,
  useResetToggle,
  useToggles,
  useUpdateToggle,
} from "@/features/settings/hooks";
import type { ToggleOut } from "@/types/models";

/**
 * Every switch carries its own label, description and warning from the
 * backend registry rather than from a translation key here. That is
 * deliberate: a toggle cannot then exist without an explanation of what
 * turning it off actually does, and the two can never drift apart.
 */
export function CounterRulesSection() {
  const { t } = useTranslation();
  const { data: toggles, isLoading, isError } = useToggles();
  const { data: series } = useInvoiceSeries();
  const update = useUpdateToggle();
  const reset = useResetToggle();

  const groups = useMemo(() => {
    const map = new Map<string, ToggleOut[]>();
    for (const toggle of toggles ?? []) {
      map.set(toggle.group, [...(map.get(toggle.group) ?? []), toggle]);
    }
    return [...map.entries()];
  }, [toggles]);

  const handleChange = async (toggle: ToggleOut, enabled: boolean) => {
    try {
      await update.mutateAsync({ key: toggle.key, enabled });
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  const handleReset = async (toggle: ToggleOut) => {
    try {
      await reset.mutateAsync(toggle.key);
      toast.success(t("counterRules.resetDone"));
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  return (
    <Card className="space-y-4 p-5">
      <div>
        <h2 className="text-sm font-semibold text-slate-900">{t("counterRules.title")}</h2>
        <p className="mt-0.5 text-xs text-slate-500">{t("counterRules.subtitle")}</p>
      </div>

      {series && (
        <div className="rounded-lg bg-slate-50 px-3 py-2 text-xs">
          <span className="text-slate-500">{t("counterRules.nextInvoice")}</span>{" "}
          <span className="font-mono font-medium text-slate-900">{series.next_number}</span>
          <span className="ml-2 text-slate-400">
            {t("counterRules.issuedSoFar", { count: series.last_issued })}
          </span>
        </div>
      )}

      {isLoading && (
        <div className="flex justify-center py-8">
          <Spinner className="text-brand-600" />
        </div>
      )}

      {isError && (
        <div className="flex items-center gap-2 py-6 text-sm text-danger-600">
          <AlertTriangle size={18} /> {t("counterRules.loadError")}
        </div>
      )}

      {groups.map(([group, items]) => (
        <div key={group} className="rounded-lg border border-slate-200">
          <div className="border-b border-slate-100 px-3 py-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            {t(`counterRules.group.${group}`, group)}
          </div>

          {items.map((toggle) => (
            <div key={toggle.key} className="border-b border-slate-50 px-3 py-3 last:border-0">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="flex items-center gap-1.5 text-sm font-medium text-slate-800">
                    {toggle.label}
                    {/* An entitlement: shown and explained, but not the
                        owner's to change. */}
                    {!toggle.owner_editable && (
                      <span
                        title={t("counterRules.planControlled")}
                        className="inline-flex items-center gap-1 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-normal text-slate-500"
                      >
                        <Lock size={10} /> {t("counterRules.planControlled")}
                      </span>
                    )}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500">{toggle.description}</p>

                  {/* Only warn when the switch is actually in the risky
                      position — a permanent warning is one people learn to
                      stop reading. */}
                  {toggle.warning && !toggle.enabled && (
                    <p className="mt-1.5 flex items-start gap-1.5 rounded bg-amber-50 px-2 py-1 text-xs text-amber-800">
                      <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                      {toggle.warning}
                    </p>
                  )}
                </div>

                <div className="flex shrink-0 items-center gap-2">
                  {toggle.is_overridden && toggle.owner_editable && (
                    <button
                      type="button"
                      title={t("counterRules.resetToDefault", {
                        value: toggle.default ? t("counterRules.on") : t("counterRules.off"),
                      })}
                      aria-label={t("counterRules.resetToDefault", {
                        value: toggle.default ? t("counterRules.on") : t("counterRules.off"),
                      })}
                      className="p-1 text-slate-400 hover:text-brand-600"
                      onClick={() => void handleReset(toggle)}
                    >
                      <RotateCcw size={13} />
                    </button>
                  )}
                  <Switch
                    checked={toggle.enabled}
                    disabled={!toggle.owner_editable}
                    onChange={(next) => void handleChange(toggle, next)}
                    label={toggle.label}
                  />
                </div>
              </div>

              {/* Distinguishes "the owner chose this" from "this is the
                  default", so a later change of default is not mistaken for
                  somebody's setting. */}
              <p className="mt-1 text-[11px] text-slate-400">
                {toggle.is_overridden
                  ? t("counterRules.chosen")
                  : t("counterRules.usingDefault", {
                      value: toggle.default ? t("counterRules.on") : t("counterRules.off"),
                    })}
              </p>
            </div>
          ))}
        </div>
      ))}
    </Card>
  );
}
