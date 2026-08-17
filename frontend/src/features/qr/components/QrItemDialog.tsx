import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { QuantityStepper } from "@/components/ui/QuantityStepper";
import { VegIndicator } from "@/components/VegIndicator";
import { formatCurrency } from "@/lib/format";
import { cn } from "@/lib/cn";
import { useQrCartStore } from "@/stores/qrCartStore";
import type { QRMenuItemOut } from "@/types/models";

export function QrItemDialog({ item, onClose }: { item: QRMenuItemOut | null; onClose: () => void }) {
  const { t } = useTranslation();
  const addLine = useQrCartStore((s) => s.addLine);

  const defaultVariantId = useMemo(() => {
    if (!item || item.variants.length === 0) return undefined;
    return item.variants.find((v) => v.is_default)?.id ?? item.variants[0]?.id;
  }, [item]);

  const [variantId, setVariantId] = useState<string | undefined>(defaultVariantId);
  const [selectedOptions, setSelectedOptions] = useState<Record<string, string[]>>({});
  const [quantity, setQuantity] = useState(1);
  const [notes, setNotes] = useState("");

  // Reset local state whenever a different item is opened.
  const [openItemId, setOpenItemId] = useState<string | undefined>(item?.id);
  if (item && item.id !== openItemId) {
    setOpenItemId(item.id);
    setVariantId(defaultVariantId);
    setSelectedOptions({});
    setQuantity(1);
    setNotes("");
  }

  if (!item) return null;

  const selectedVariant = item.variants.find((v) => v.id === variantId);

  const toggleOption = (groupId: string, optionId: string, allowMultiple: boolean) => {
    setSelectedOptions((prev) => {
      const current = prev[groupId] ?? [];
      if (allowMultiple) {
        const next = current.includes(optionId)
          ? current.filter((id) => id !== optionId)
          : [...current, optionId];
        return { ...prev, [groupId]: next };
      }
      return { ...prev, [groupId]: [optionId] };
    });
  };

  const missingRequiredGroup = item.option_groups.find(
    (g) => g.is_required && (selectedOptions[g.id]?.length ?? 0) === 0
  );
  const canAdd = (item.variants.length === 0 || Boolean(variantId)) && !missingRequiredGroup;

  const allSelectedOptions = item.option_groups.flatMap((g) =>
    g.options.filter((o) => selectedOptions[g.id]?.includes(o.id))
  );

  const unitEstimate = item.price + (selectedVariant?.price_delta ?? 0);
  const optionsTotal = allSelectedOptions.reduce((s, o) => s + o.price_delta, 0);
  const lineEstimate = (unitEstimate + optionsTotal) * quantity;

  const handleAdd = () => {
    addLine({
      menuItemId: item.id,
      itemName: item.name,
      isVeg: item.is_veg,
      unitEstimate,
      variantId: selectedVariant?.id,
      variantName: selectedVariant?.name,
      options: allSelectedOptions.map((o) => ({ id: o.id, name: o.name, priceDelta: o.price_delta })),
      quantity,
      specialInstructions: notes.trim() || undefined,
    });
    onClose();
  };

  return (
    <Dialog
      open={Boolean(item)}
      onClose={onClose}
      title={item.name}
      footer={
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs text-stone-500">{t("pos.estimatedTotal")}</p>
            <p className="text-lg font-bold text-stone-900">{formatCurrency(lineEstimate)}</p>
          </div>
          <Button size="lg" onClick={handleAdd} disabled={!canAdd}>
            {t("pos.addToCart")}
          </Button>
        </div>
      }
    >
      <div className="flex items-start gap-2">
        <VegIndicator isVeg={item.is_veg} />
        <div>{item.description && <p className="text-sm text-stone-500">{item.description}</p>}</div>
      </div>

      {item.variants.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-500">{t("pos.selectSize")}</p>
          <div className="space-y-1.5">
            {item.variants.map((v) => (
              <label
                key={v.id}
                className={cn(
                  "flex cursor-pointer items-center justify-between rounded-lg border px-3 py-2 text-sm",
                  variantId === v.id ? "border-brand-500 bg-brand-50" : "border-stone-200 hover:bg-stone-50"
                )}
              >
                <span className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="variant"
                    checked={variantId === v.id}
                    onChange={() => setVariantId(v.id)}
                    className="accent-brand-600"
                  />
                  {v.name}
                </span>
                <span className="font-medium text-stone-600">{formatCurrency(item.price + v.price_delta)}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {item.option_groups.map((group) => (
        <div key={group.id} className="mt-4">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-stone-500">
            {group.name}
            {group.is_required && <span className="text-danger-500">*</span>}
          </p>
          <div className="space-y-1.5">
            {group.options.map((o) => {
              const checked = (selectedOptions[group.id] ?? []).includes(o.id);
              return (
                <label
                  key={o.id}
                  className={cn(
                    "flex cursor-pointer items-center justify-between rounded-lg border px-3 py-2 text-sm",
                    checked ? "border-brand-500 bg-brand-50" : "border-stone-200 hover:bg-stone-50"
                  )}
                >
                  <span className="flex items-center gap-2">
                    <input
                      type={group.allow_multiple ? "checkbox" : "radio"}
                      name={`group-${group.id}`}
                      checked={checked}
                      onChange={() => toggleOption(group.id, o.id, group.allow_multiple)}
                      className="accent-brand-600"
                    />
                    {o.name}
                  </span>
                  {o.price_delta !== 0 && (
                    <span className="font-medium text-stone-600">+{formatCurrency(o.price_delta)}</span>
                  )}
                </label>
              );
            })}
          </div>
        </div>
      ))}

      <div className="mt-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-500">{t("pos.notes")}</p>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          maxLength={500}
          placeholder={t("pos.notesPlaceholder")}
          className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm focus-ring"
        />
      </div>

      <div className="mt-4 flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">{t("pos.quantity")}</p>
        <QuantityStepper value={quantity} onChange={setQuantity} min={1} />
      </div>
    </Dialog>
  );
}
