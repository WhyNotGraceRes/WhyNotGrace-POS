import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Switch } from "@/components/ui/Switch";
import { formatCurrency } from "@/lib/format";
import { parseApiError } from "@/api/errors";
import { useCreatePriceRule, useDeletePriceRule, usePriceRules, useUpdatePriceRule } from "@/features/pricing/hooks";
import type { MenuItemOut, MenuVariantOut, PricingContext } from "@/types/models";

const CONTEXTS: PricingContext[] = [
  "DINE_IN",
  "PICKUP",
  "DELIVERY",
  "ROOM_SERVICE",
  "SECTION_A",
  "SECTION_B",
  "POOL_AREA",
  "LOUNGE",
  "CUSTOM",
];

export function PriceRulesSection({ item }: { item: MenuItemOut }) {
  const { t } = useTranslation();
  const { data: rules, isLoading } = usePriceRules(item.id);
  const createRule = useCreatePriceRule();
  const updateRule = useUpdatePriceRule();
  const deleteRule = useDeletePriceRule();

  const [context, setContext] = useState<PricingContext>("PICKUP");
  const [variantId, setVariantId] = useState<string>("");
  const [price, setPrice] = useState("");
  const [error, setError] = useState<string | null>(null);

  const variantName = (id: string | null) => (item.variants.find((v: MenuVariantOut) => v.id === id)?.name ?? null);

  const handleAdd = () => {
    setError(null);
    const priceNum = Number(price);
    if (!(priceNum > 0)) {
      setError(t("menuAdmin.priceRuleInvalid"));
      return;
    }
    createRule.mutate(
      { item_id: item.id, context, price: priceNum, variant_id: variantId || undefined },
      {
        onSuccess: () => {
          setPrice("");
          toast.success(t("menuAdmin.priceRuleAdded"));
        },
        onError: (err) => setError(parseApiError(err).message),
      }
    );
  };

  return (
    <div className="rounded-lg border border-slate-200 p-3">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{t("menuAdmin.pricingRules")}</p>
      {error && <p className="mb-2 text-xs text-danger-600">{error}</p>}

      {isLoading ? (
        <p className="text-xs text-slate-400">{t("common.loading")}</p>
      ) : (rules ?? []).length === 0 ? (
        <p className="mb-2 text-xs text-slate-400">{t("menuAdmin.none")}</p>
      ) : (
        <ul className="mb-3 space-y-1.5">
          {(rules ?? []).map((rule) => (
            <li key={rule.id} className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-2.5 py-1.5 text-xs">
              <span className="text-slate-700">
                {t(`pricingContext.${rule.context}`)}
                {variantName(rule.variant_id) && ` · ${variantName(rule.variant_id)}`}
              </span>
              <span className="flex items-center gap-2">
                <span className="font-semibold text-slate-800">{formatCurrency(rule.price)}</span>
                <Switch
                  checked={rule.is_active}
                  onChange={(checked) => updateRule.mutate({ ruleId: rule.id, payload: { is_active: checked } })}
                  label={t("menuAdmin.isActive")}
                />
                <button
                  type="button"
                  onClick={() => deleteRule.mutate(rule.id)}
                  className="text-slate-400 hover:text-danger-600"
                  aria-label={t("menuAdmin.deletePriceRule")}
                >
                  <Trash2 size={13} />
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}

      <div className="flex flex-wrap items-end gap-2 border-t border-slate-100 pt-3">
        <div className="min-w-[8rem]">
          <Select value={context} onChange={(e) => setContext(e.target.value as PricingContext)}>
            {CONTEXTS.map((c) => (
              <option key={c} value={c}>
                {t(`pricingContext.${c}`)}
              </option>
            ))}
          </Select>
        </div>
        {item.variants.length > 0 && (
          <div className="min-w-[8rem]">
            <Select value={variantId} onChange={(e) => setVariantId(e.target.value)}>
              <option value="">{t("menuAdmin.allVariants")}</option>
              {item.variants.map((v: MenuVariantOut) => (
                <option key={v.id} value={v.id}>
                  {v.name}
                </option>
              ))}
            </Select>
          </div>
        )}
        <div className="w-28">
          <Input type="number" min={0.01} step="0.01" placeholder={t("menuAdmin.basePrice")} value={price} onChange={(e) => setPrice(e.target.value)} />
        </div>
        <Button type="button" variant="secondary" isLoading={createRule.isPending} onClick={handleAdd}>
          <Plus size={14} />
          {t("menuAdmin.add")}
        </Button>
      </div>
    </div>
  );
}
