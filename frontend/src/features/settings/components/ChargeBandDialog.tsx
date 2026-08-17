import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";

import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { Switch } from "@/components/ui/Switch";
import { parseApiError } from "@/api/errors";
import { useCreateChargeBand, useUpdateChargeBand } from "@/features/settings/hooks";
import type { ChargeBandOut, ChargeBasis, PricingContext } from "@/types/models";

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

export function ChargeBandDialog({
  open,
  onClose,
  band,
  defaultName,
}: {
  open: boolean;
  onClose: () => void;
  band: ChargeBandOut | null;
  defaultName?: string;
}) {
  const { t } = useTranslation();
  const create = useCreateChargeBand();
  const update = useUpdateChargeBand();

  const [name, setName] = useState(band?.name ?? defaultName ?? "");
  const [context, setContext] = useState<string>(band?.applies_to_context ?? "");
  const [minAmount, setMinAmount] = useState(String(band?.min_amount ?? 0));
  // An empty upper bound means "and above" — the open-ended top of a ladder.
  const [maxAmount, setMaxAmount] = useState(band?.max_amount == null ? "" : String(band.max_amount));
  const [basis, setBasis] = useState<ChargeBasis>(band?.basis ?? "FLAT");
  const [value, setValue] = useState(String(band?.value ?? 0));
  const [isTaxable, setIsTaxable] = useState(band?.is_taxable ?? true);
  const [isActive, setIsActive] = useState(band?.is_active ?? true);
  const [error, setError] = useState<string | null>(null);

  const isPending = create.isPending || update.isPending;

  const handleSave = async () => {
    setError(null);
    const payload = {
      name: name.trim(),
      applies_to_context: context ? (context as PricingContext) : null,
      min_amount: Number(minAmount) || 0,
      max_amount: maxAmount.trim() === "" ? null : Number(maxAmount),
      basis,
      value: Number(value) || 0,
      is_taxable: isTaxable,
      is_active: isActive,
      display_order: band?.display_order ?? 0,
    };
    try {
      if (band) {
        await update.mutateAsync({ bandId: band.id, payload });
      } else {
        await create.mutateAsync(payload);
      }
      toast.success(t("charges.saved"));
      onClose();
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={band ? t("charges.editBand") : t("charges.addBand")}
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button isLoading={isPending} onClick={() => void handleSave()}>
            {t("common.save")}
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {error && (
          <p className="rounded-lg border border-danger-500/30 bg-danger-50 px-3 py-2 text-xs text-danger-700">
            {error}
          </p>
        )}

        <div>
          <Label htmlFor="band-name">{t("charges.chargeName")}</Label>
          <Input
            id="band-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t("charges.chargeNamePlaceholder")}
          />
          <p className="mt-1 text-xs text-stone-500">{t("charges.chargeNameHint")}</p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="band-min">{t("charges.fromAmount")}</Label>
            <Input
              id="band-min"
              type="number"
              min={0}
              step="0.01"
              value={minAmount}
              onChange={(e) => setMinAmount(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="band-max">{t("charges.toAmount")}</Label>
            <Input
              id="band-max"
              type="number"
              min={0}
              step="0.01"
              value={maxAmount}
              onChange={(e) => setMaxAmount(e.target.value)}
              placeholder={t("charges.noUpperLimit")}
            />
          </div>
        </div>
        {/* The half-open boundary is the single most confusable thing on
            this screen, so it is spelled out rather than implied. */}
        <p className="-mt-2 text-xs text-stone-500">{t("charges.rangeHint")}</p>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="band-basis">{t("charges.basis")}</Label>
            <Select id="band-basis" value={basis} onChange={(e) => setBasis(e.target.value as ChargeBasis)}>
              <option value="FLAT">{t("charges.basisFlat")}</option>
              <option value="PERCENT">{t("charges.basisPercent")}</option>
            </Select>
          </div>
          <div>
            <Label htmlFor="band-value">
              {basis === "PERCENT" ? t("charges.valuePercent") : t("charges.valueFlat")}
            </Label>
            <Input
              id="band-value"
              type="number"
              min={0}
              step="0.01"
              value={value}
              onChange={(e) => setValue(e.target.value)}
            />
          </div>
        </div>
        <p className="-mt-2 text-xs text-stone-500">{t("charges.zeroHint")}</p>

        <div>
          <Label htmlFor="band-context">{t("charges.appliesTo")}</Label>
          <Select id="band-context" value={context} onChange={(e) => setContext(e.target.value)}>
            <option value="">{t("charges.allContexts")}</option>
            {CONTEXTS.map((c) => (
              <option key={c} value={c}>
                {t(`charges.context.${c}`, c.replace(/_/g, " "))}
              </option>
            ))}
          </Select>
        </div>

        <div className="flex items-center justify-between rounded-lg border border-stone-200 px-3 py-2">
          <div>
            <p className="text-sm font-medium text-stone-800">{t("charges.taxable")}</p>
            <p className="text-xs text-stone-500">{t("charges.taxableHint")}</p>
          </div>
          <Switch checked={isTaxable} onChange={setIsTaxable} label={t("charges.taxable")} />
        </div>

        <div className="flex items-center justify-between rounded-lg border border-stone-200 px-3 py-2">
          <p className="text-sm font-medium text-stone-800">{t("charges.active")}</p>
          <Switch checked={isActive} onChange={setIsActive} label={t("charges.active")} />
        </div>
      </div>
    </Dialog>
  );
}
