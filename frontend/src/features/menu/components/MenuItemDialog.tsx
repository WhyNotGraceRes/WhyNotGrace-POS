import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { Plus, Trash2, X } from "lucide-react";

import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { Switch } from "@/components/ui/Switch";
import { formatCurrency } from "@/lib/format";
import { cn } from "@/lib/cn";
import { parseApiError } from "@/api/errors";
import {
  useAddOption,
  useAddOptionGroup,
  useAddVariant,
  useCreateMenuItem,
  useDeleteMenuItem,
  useDeleteOption,
  useDeleteOptionGroup,
  useDeleteVariant,
  useUpdateMenuItem,
} from "@/features/menu/hooks";
import { PriceRulesSection } from "@/features/menu/components/PriceRulesSection";
import { ItemTranslationsSection } from "@/features/menu/components/ItemTranslationsSection";
import type { MenuCategoryOut, MenuItemOut, MenuOptionCreate, MenuVariantCreate } from "@/types/models";

interface DraftVariant extends MenuVariantCreate {
  key: string;
}
interface DraftOptionGroup {
  key: string;
  name: string;
  is_required: boolean;
  allow_multiple: boolean;
  options: (MenuOptionCreate & { key: string })[];
}

export function MenuItemDialog({
  open,
  item,
  categories,
  defaultCategoryId,
  onClose,
}: {
  open: boolean;
  item: MenuItemOut | null;
  categories: MenuCategoryOut[];
  defaultCategoryId?: string;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const isEdit = Boolean(item);

  const createItem = useCreateMenuItem();
  const updateItem = useUpdateMenuItem();
  const deleteItem = useDeleteMenuItem();
  const addVariant = useAddVariant();
  const addOptionGroup = useAddOptionGroup();
  const addOption = useAddOption();
  const deleteVariant = useDeleteVariant();
  const deleteOptionGroup = useDeleteOptionGroup();
  const deleteOption = useDeleteOption();

  const [name, setName] = useState(item?.name ?? "");
  const [description, setDescription] = useState(item?.description ?? "");
  const [basePrice, setBasePrice] = useState(String(item?.base_price ?? ""));
  const [categoryId, setCategoryId] = useState(item?.category_id ?? defaultCategoryId ?? categories[0]?.id ?? "");
  const [isVeg, setIsVeg] = useState(item?.is_veg ?? true);
  const [imageUrl, setImageUrl] = useState(item?.image_url ?? "");
  const [isActive, setIsActive] = useState(item?.is_active ?? true);
  const [isSoldOut, setIsSoldOut] = useState(item?.is_sold_out ?? false);
  const [isTodaysSpecial, setIsTodaysSpecial] = useState(item?.is_todays_special ?? false);
  const [isSpecialty, setIsSpecialty] = useState(item?.is_specialty ?? false);
  const [stockQuantity, setStockQuantity] = useState(item?.stock_quantity != null ? String(item.stock_quantity) : "");
  const [kitchenStation, setKitchenStation] = useState(item?.kitchen_station ?? "");
  const [error, setError] = useState<string | null>(null);

  // Only used while creating a brand-new item — added variants/groups on an
  // existing item go straight to the backend via the ADD endpoints instead.
  const [draftVariants, setDraftVariants] = useState<DraftVariant[]>([]);
  const [draftGroups, setDraftGroups] = useState<DraftOptionGroup[]>([]);

  const [newVariantName, setNewVariantName] = useState("");
  const [newVariantDelta, setNewVariantDelta] = useState("0");
  const [newGroupName, setNewGroupName] = useState("");
  const [newGroupRequired, setNewGroupRequired] = useState(false);
  const [newGroupMultiple, setNewGroupMultiple] = useState(false);
  const [newOptionNameByGroup, setNewOptionNameByGroup] = useState<Record<string, string>>({});
  const [newOptionDeltaByGroup, setNewOptionDeltaByGroup] = useState<Record<string, string>>({});

  const [openItemId, setOpenItemId] = useState<string | null>(item?.id ?? null);
  // Tracks whether the dialog was open on the previous render so that
  // reopening it for a brand-new item (item stays null across opens, so
  // openItemId never changes) still re-derives categoryId from the latest
  // categories list — otherwise a categoryId computed before any category
  // existed would stick empty forever, since this component stays mounted
  // across dialog open/close rather than remounting.
  const [wasOpen, setWasOpen] = useState(open);
  if (open && ((item?.id ?? null) !== openItemId || !wasOpen)) {
    setOpenItemId(item?.id ?? null);
    setName(item?.name ?? "");
    setDescription(item?.description ?? "");
    setBasePrice(String(item?.base_price ?? ""));
    setCategoryId(item?.category_id ?? defaultCategoryId ?? categories[0]?.id ?? "");
    setIsVeg(item?.is_veg ?? true);
    setImageUrl(item?.image_url ?? "");
    setIsActive(item?.is_active ?? true);
    setIsSoldOut(item?.is_sold_out ?? false);
    setIsTodaysSpecial(item?.is_todays_special ?? false);
    setIsSpecialty(item?.is_specialty ?? false);
    setStockQuantity(item?.stock_quantity != null ? String(item.stock_quantity) : "");
    setKitchenStation(item?.kitchen_station ?? "");
    setError(null);
    setDraftVariants([]);
    setDraftGroups([]);
  }
  if (open !== wasOpen) setWasOpen(open);

  if (!open) return null;

  const isPending = createItem.isPending || updateItem.isPending;

  const handleSubmit = async () => {
    setError(null);
    const price = Number(basePrice);
    if (!name.trim() || !categoryId || !(price > 0)) {
      setError(t("menuAdmin.itemFieldsRequired"));
      return;
    }
    // Empty field means untracked/unlimited — null on update explicitly
    // clears server-side tracking, undefined on create just omits it.
    const stockQuantityValue = stockQuantity.trim() === "" ? null : Number(stockQuantity);
    try {
      if (isEdit && item) {
        await updateItem.mutateAsync({
          itemId: item.id,
          payload: {
            name: name.trim(),
            description: description.trim() || null,
            base_price: price,
            category_id: categoryId,
            is_veg: isVeg,
            image_url: imageUrl.trim() || null,
            is_active: isActive,
            is_sold_out: isSoldOut,
            is_todays_special: isTodaysSpecial,
            is_specialty: isSpecialty,
            stock_quantity: stockQuantityValue,
            kitchen_station: kitchenStation.trim() || null,
          },
        });
        toast.success(t("menuAdmin.itemUpdated"));
      } else {
        await createItem.mutateAsync({
          name: name.trim(),
          description: description.trim() || undefined,
          base_price: price,
          category_id: categoryId,
          is_veg: isVeg,
          image_url: imageUrl.trim() || undefined,
          stock_quantity: stockQuantityValue ?? undefined,
          kitchen_station: kitchenStation.trim() || undefined,
          variants: draftVariants.map(({ key: _key, ...v }) => v),
          option_groups: draftGroups.map((g) => ({
            name: g.name,
            is_required: g.is_required,
            allow_multiple: g.allow_multiple,
            options: g.options.map(({ key: _key, ...o }) => o),
          })),
        });
        toast.success(t("menuAdmin.itemCreated"));
      }
      onClose();
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const handleDelete = async () => {
    if (!item) return;
    if (!window.confirm(t("menuAdmin.confirmDeleteItem", { name: item.name }))) return;
    try {
      await deleteItem.mutateAsync(item.id);
      toast.success(t("menuAdmin.itemDeleted"));
      onClose();
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const handleAddVariantDraft = () => {
    if (!newVariantName.trim()) return;
    setDraftVariants((prev) => [
      ...prev,
      { key: crypto.randomUUID(), name: newVariantName.trim(), price_delta: Number(newVariantDelta) || 0 },
    ]);
    setNewVariantName("");
    setNewVariantDelta("0");
  };

  const handleAddGroupDraft = () => {
    if (!newGroupName.trim()) return;
    setDraftGroups((prev) => [
      ...prev,
      { key: crypto.randomUUID(), name: newGroupName.trim(), is_required: newGroupRequired, allow_multiple: newGroupMultiple, options: [] },
    ]);
    setNewGroupName("");
    setNewGroupRequired(false);
    setNewGroupMultiple(false);
  };

  const handleAddOptionDraft = (groupKey: string) => {
    const optName = (newOptionNameByGroup[groupKey] ?? "").trim();
    if (!optName) return;
    setDraftGroups((prev) =>
      prev.map((g) =>
        g.key === groupKey
          ? {
              ...g,
              options: [
                ...g.options,
                { key: crypto.randomUUID(), name: optName, price_delta: Number(newOptionDeltaByGroup[groupKey]) || 0 },
              ],
            }
          : g
      )
    );
    setNewOptionNameByGroup((prev) => ({ ...prev, [groupKey]: "" }));
    setNewOptionDeltaByGroup((prev) => ({ ...prev, [groupKey]: "0" }));
  };

  const handleAddVariantLive = () => {
    if (!item || !newVariantName.trim()) return;
    addVariant.mutate(
      { itemId: item.id, payload: { name: newVariantName.trim(), price_delta: Number(newVariantDelta) || 0 } },
      {
        onSuccess: () => {
          setNewVariantName("");
          setNewVariantDelta("0");
          toast.success(t("menuAdmin.variantAdded"));
        },
        onError: (err) => setError(parseApiError(err).message),
      }
    );
  };

  const handleAddGroupLive = () => {
    if (!item || !newGroupName.trim()) return;
    addOptionGroup.mutate(
      { itemId: item.id, payload: { name: newGroupName.trim(), is_required: newGroupRequired, allow_multiple: newGroupMultiple } },
      {
        onSuccess: () => {
          setNewGroupName("");
          setNewGroupRequired(false);
          setNewGroupMultiple(false);
          toast.success(t("menuAdmin.optionGroupAdded"));
        },
        onError: (err) => setError(parseApiError(err).message),
      }
    );
  };

  const handleDeleteVariant = (variantId: string, name: string) => {
    if (!window.confirm(t("menuAdmin.confirmDeleteVariant", { name }))) return;
    deleteVariant.mutate(variantId, {
      onSuccess: () => toast.success(t("menuAdmin.variantDeleted")),
      onError: (err) => toast.error(parseApiError(err).message),
    });
  };

  const handleDeleteOptionGroup = (groupId: string, name: string) => {
    if (!window.confirm(t("menuAdmin.confirmDeleteOptionGroup", { name }))) return;
    deleteOptionGroup.mutate(groupId, {
      onSuccess: () => toast.success(t("menuAdmin.optionGroupDeleted")),
      onError: (err) => toast.error(parseApiError(err).message),
    });
  };

  const handleDeleteOption = (optionId: string, name: string) => {
    if (!window.confirm(t("menuAdmin.confirmDeleteOption", { name }))) return;
    deleteOption.mutate(optionId, {
      onSuccess: () => toast.success(t("menuAdmin.optionDeleted")),
      onError: (err) => toast.error(parseApiError(err).message),
    });
  };

  const handleAddOptionLive = (groupId: string) => {
    const optName = (newOptionNameByGroup[groupId] ?? "").trim();
    if (!optName) return;
    addOption.mutate(
      { groupId, payload: { name: optName, price_delta: Number(newOptionDeltaByGroup[groupId]) || 0 } },
      {
        onSuccess: () => {
          setNewOptionNameByGroup((prev) => ({ ...prev, [groupId]: "" }));
          setNewOptionDeltaByGroup((prev) => ({ ...prev, [groupId]: "0" }));
          toast.success(t("menuAdmin.optionAdded"));
        },
        onError: (err) => setError(parseApiError(err).message),
      }
    );
  };

  return (
    <Dialog open={open} onClose={onClose} title={isEdit ? t("menuAdmin.editItem") : t("menuAdmin.addItem")} size="lg">
      <div className="space-y-4">
        {error && <p className="rounded-lg border border-danger-500/30 bg-danger-50 px-3 py-2 text-xs text-danger-700">{error}</p>}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <Label htmlFor="item-name">{t("menuAdmin.name")}</Label>
            <Input id="item-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="item-category">{t("menuAdmin.category")}</Label>
            <Select id="item-category" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label htmlFor="item-price">{t("menuAdmin.basePrice")}</Label>
            <Input id="item-price" type="number" min={0.01} step="0.01" value={basePrice} onChange={(e) => setBasePrice(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="item-image">{t("menuAdmin.imageUrl")}</Label>
            <Input id="item-image" value={imageUrl} onChange={(e) => setImageUrl(e.target.value)} placeholder="https://…" />
          </div>
          <div>
            <Label htmlFor="item-stock">{t("menuAdmin.stockQuantity")}</Label>
            <Input
              id="item-stock"
              type="number"
              min={0}
              step="1"
              value={stockQuantity}
              onChange={(e) => setStockQuantity(e.target.value)}
              placeholder={t("menuAdmin.stockUnlimited")}
            />
            <p className="mt-1 text-xs text-stone-400">{t("menuAdmin.stockQuantityHint")}</p>
          </div>
          <div>
            <Label htmlFor="item-station">{t("menuAdmin.kitchenStation")}</Label>
            <Input
              id="item-station"
              value={kitchenStation}
              onChange={(e) => setKitchenStation(e.target.value)}
              placeholder={t("menuAdmin.kitchenStationPlaceholder")}
            />
            <p className="mt-1 text-xs text-stone-400">{t("menuAdmin.kitchenStationHint")}</p>
          </div>
        </div>

        <div>
          <Label htmlFor="item-desc">{t("menuAdmin.description")}</Label>
          <Input id="item-desc" value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>

        <div className="flex flex-wrap gap-4">
          <label className="flex items-center gap-2 text-sm text-stone-700">
            <Switch checked={isVeg} onChange={setIsVeg} label={t("menuAdmin.isVeg")} />
            {t("menuAdmin.isVeg")}
          </label>
          {isEdit && (
            <>
              <label className="flex items-center gap-2 text-sm text-stone-700">
                <Switch checked={isActive} onChange={setIsActive} label={t("menuAdmin.isActive")} />
                {t("menuAdmin.isActive")}
              </label>
              <label className="flex items-center gap-2 text-sm text-stone-700">
                <Switch checked={isSoldOut} onChange={setIsSoldOut} label={t("pos.soldOut")} />
                {t("pos.soldOut")}
              </label>
              <label className="flex items-center gap-2 text-sm text-stone-700">
                <Switch checked={isTodaysSpecial} onChange={setIsTodaysSpecial} label={t("pos.special")} />
                {t("pos.special")}
              </label>
              <label className="flex items-center gap-2 text-sm text-stone-700">
                <Switch checked={isSpecialty} onChange={setIsSpecialty} label={t("menuAdmin.isSpecialty")} />
                {t("menuAdmin.isSpecialty")}
              </label>
            </>
          )}
        </div>

        {/* Variants */}
        <div className="rounded-lg border border-stone-200 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-500">{t("menuAdmin.variants")}</p>
          <div className="mb-2 flex flex-wrap gap-1.5">
            {(isEdit ? item?.variants ?? [] : draftVariants).map((v) => {
              const delta = v.price_delta ?? 0;
              const isSaved = "id" in v;
              return (
                <span
                  key={isSaved ? v.id : v.key}
                  className={cn(
                    "flex items-center gap-1 rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-700",
                    isSaved && "is_active" in v && !v.is_active && "opacity-50"
                  )}
                >
                  {v.name} {delta !== 0 && `(${formatCurrency(delta)})`}
                  {"is_default" in v && v.is_default && ` · ${t("menuAdmin.default")}`}
                  {isSaved && (
                    <button
                      type="button"
                      onClick={() => handleDeleteVariant(v.id, v.name)}
                      className="ml-0.5 rounded-full p-0.5 text-stone-400 hover:bg-danger-50 hover:text-danger-600"
                      aria-label={t("menuAdmin.deleteVariant")}
                    >
                      <X size={11} />
                    </button>
                  )}
                </span>
              );
            })}
            {(isEdit ? item?.variants.length === 0 : draftVariants.length === 0) && (
              <span className="text-xs text-stone-400">{t("menuAdmin.none")}</span>
            )}
          </div>
          <div className="flex flex-wrap items-end gap-2">
            <div className="min-w-[9rem] flex-1">
              <Label htmlFor="new-variant-name">{t("menuAdmin.variantName")}</Label>
              <Input id="new-variant-name" value={newVariantName} onChange={(e) => setNewVariantName(e.target.value)} />
            </div>
            <div className="w-28">
              <Label htmlFor="new-variant-delta">{t("menuAdmin.priceDelta")}</Label>
              <Input id="new-variant-delta" type="number" step="0.01" value={newVariantDelta} onChange={(e) => setNewVariantDelta(e.target.value)} />
            </div>
            <Button
              type="button"
              variant="secondary"
              size="md"
              isLoading={addVariant.isPending}
              onClick={isEdit ? handleAddVariantLive : handleAddVariantDraft}
            >
              <Plus size={14} />
              {t("menuAdmin.add")}
            </Button>
          </div>
        </div>

        {/* Option groups */}
        <div className="rounded-lg border border-stone-200 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-500">{t("menuAdmin.optionGroups")}</p>
          <div className="space-y-3">
            {(isEdit ? item?.option_groups ?? [] : draftGroups).map((g) => {
              const groupIsSaved = "id" in g;
              const groupKey = groupIsSaved ? g.id : g.key;
              return (
              <div
                key={groupKey}
                className={cn("rounded-lg bg-stone-50 p-2.5", groupIsSaved && "is_active" in g && !g.is_active && "opacity-50")}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-semibold text-stone-800">
                    {g.name}
                    {g.is_required && <span className="ml-1.5 text-[10px] font-bold uppercase text-danger-500">{t("menuAdmin.required")}</span>}
                    {g.allow_multiple && <span className="ml-1.5 text-[10px] font-bold uppercase text-stone-400">{t("menuAdmin.multiple")}</span>}
                  </p>
                  {groupIsSaved && (
                    <button
                      type="button"
                      onClick={() => handleDeleteOptionGroup(g.id, g.name)}
                      className="shrink-0 rounded p-0.5 text-stone-400 hover:bg-danger-50 hover:text-danger-600"
                      aria-label={t("menuAdmin.deleteOptionGroup")}
                    >
                      <Trash2 size={12} />
                    </button>
                  )}
                </div>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {g.options.map((o) => {
                    const delta = o.price_delta ?? 0;
                    const optionIsSaved = "id" in o;
                    return (
                      <span
                        key={optionIsSaved ? o.id : o.key}
                        className={cn(
                          "flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-xs text-stone-600",
                          optionIsSaved && "is_active" in o && !o.is_active && "opacity-50"
                        )}
                      >
                        {o.name} {delta !== 0 && `(${formatCurrency(delta)})`}
                        {optionIsSaved && (
                          <button
                            type="button"
                            onClick={() => handleDeleteOption(o.id, o.name)}
                            className="ml-0.5 rounded-full p-0.5 text-stone-400 hover:bg-danger-50 hover:text-danger-600"
                            aria-label={t("menuAdmin.deleteOption")}
                          >
                            <X size={10} />
                          </button>
                        )}
                      </span>
                    );
                  })}
                  {g.options.length === 0 && <span className="text-xs text-stone-400">{t("menuAdmin.none")}</span>}
                </div>
                <div className="mt-2 flex flex-wrap items-end gap-2">
                  <div className="min-w-[8rem] flex-1">
                    <Input
                      placeholder={t("menuAdmin.optionName")}
                      value={newOptionNameByGroup[groupKey] ?? ""}
                      onChange={(e) => setNewOptionNameByGroup((prev) => ({ ...prev, [groupKey]: e.target.value }))}
                    />
                  </div>
                  <div className="w-24">
                    <Input
                      type="number"
                      step="0.01"
                      placeholder="+0"
                      value={newOptionDeltaByGroup[groupKey] ?? "0"}
                      onChange={(e) => setNewOptionDeltaByGroup((prev) => ({ ...prev, [groupKey]: e.target.value }))}
                    />
                  </div>
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    isLoading={addOption.isPending}
                    onClick={() =>
                      isEdit && "id" in g ? handleAddOptionLive(g.id) : handleAddOptionDraft((g as DraftOptionGroup).key)
                    }
                  >
                    <Plus size={12} />
                  </Button>
                </div>
              </div>
              );
            })}
            {(isEdit ? item?.option_groups.length === 0 : draftGroups.length === 0) && (
              <p className="text-xs text-stone-400">{t("menuAdmin.none")}</p>
            )}
          </div>

          <div className="mt-3 flex flex-wrap items-end gap-2 border-t border-stone-100 pt-3">
            <div className="min-w-[8rem] flex-1">
              <Label htmlFor="new-group-name">{t("menuAdmin.groupName")}</Label>
              <Input id="new-group-name" value={newGroupName} onChange={(e) => setNewGroupName(e.target.value)} />
            </div>
            <label className="flex items-center gap-1.5 pb-2 text-xs text-stone-600">
              <Switch checked={newGroupRequired} onChange={setNewGroupRequired} label={t("menuAdmin.required")} />
              {t("menuAdmin.required")}
            </label>
            <label className="flex items-center gap-1.5 pb-2 text-xs text-stone-600">
              <Switch checked={newGroupMultiple} onChange={setNewGroupMultiple} label={t("menuAdmin.multiple")} />
              {t("menuAdmin.multiple")}
            </label>
            <Button
              type="button"
              variant="secondary"
              size="md"
              isLoading={addOptionGroup.isPending}
              onClick={isEdit ? handleAddGroupLive : handleAddGroupDraft}
            >
              <Plus size={14} />
              {t("menuAdmin.addGroup")}
            </Button>
          </div>
        </div>

        {isEdit && item && <PriceRulesSection item={item} />}
        {isEdit && item && <ItemTranslationsSection item={item} />}

        <div className="flex items-center gap-2 pt-2">
          <Button className="flex-1" size="lg" isLoading={isPending} onClick={() => void handleSubmit()}>
            {isEdit ? t("common.save") : t("menuAdmin.addItem")}
          </Button>
          {isEdit && (
            <Button variant="danger" size="lg" isLoading={deleteItem.isPending} onClick={() => void handleDelete()}>
              <Trash2 size={16} />
            </Button>
          )}
        </div>
      </div>
    </Dialog>
  );
}
