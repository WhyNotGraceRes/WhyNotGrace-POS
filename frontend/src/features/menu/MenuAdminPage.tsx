import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { AlertTriangle, Pencil, Plus, Trash2 } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { VegIndicator } from "@/components/VegIndicator";
import { formatCurrency } from "@/lib/format";
import { cn } from "@/lib/cn";
import { parseApiError } from "@/api/errors";
import { useCategories, useDeleteCategory, useMenuItems } from "@/features/menu/hooks";
import { CategoryFormDialog } from "@/features/menu/components/CategoryFormDialog";
import { MenuItemDialog } from "@/features/menu/components/MenuItemDialog";
import type { MenuCategoryOut } from "@/types/models";

export function MenuAdminPage() {
  const { t } = useTranslation();
  const { data: categories, isLoading: categoriesLoading, isError: categoriesError } = useCategories();
  const { data: items, isLoading: itemsLoading, isError: itemsError } = useMenuItems();
  const deleteCategory = useDeleteCategory();

  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null);
  const [categoryDialogOpen, setCategoryDialogOpen] = useState(false);
  const [editingCategoryId, setEditingCategoryId] = useState<string | null>(null);
  const [itemDialogOpen, setItemDialogOpen] = useState(false);
  const [editingItemId, setEditingItemId] = useState<string | null>(null);

  // Derived from the live query result (not a snapshot) so that mutations
  // made from inside the dialog — adding a variant, option group, or price
  // rule — are reflected immediately once they invalidate the query,
  // instead of the dialog being stuck showing what the item looked like
  // when it was first opened.
  const editingCategory = categories?.find((c) => c.id === editingCategoryId) ?? null;
  const editingItem = items?.find((i) => i.id === editingItemId) ?? null;

  const visibleItems = useMemo(() => {
    if (!items) return [];
    return selectedCategoryId ? items.filter((i) => i.category_id === selectedCategoryId) : items;
  }, [items, selectedCategoryId]);

  const isLoading = categoriesLoading || itemsLoading;
  const isError = categoriesError || itemsError;

  const handleDeleteCategory = async (category: MenuCategoryOut) => {
    if (!window.confirm(t("menuAdmin.confirmDeleteCategory", { name: category.name }))) return;
    try {
      await deleteCategory.mutateAsync(category.id);
      toast.success(t("menuAdmin.categoryDeleted"));
      if (selectedCategoryId === category.id) setSelectedCategoryId(null);
    } catch (err) {
      toast.error(parseApiError(err).message);
    }
  };

  return (
    <div>
      <PageHeader
        title={t("nav.menu")}
        subtitle={t("menuAdmin.subtitle")}
        actions={
          <Button
            onClick={() => {
              setEditingItemId(null);
              setItemDialogOpen(true);
            }}
            disabled={!categories || categories.length === 0}
          >
            <Plus size={16} />
            {t("menuAdmin.addItem")}
          </Button>
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
          <p className="text-sm font-medium">{t("menuAdmin.loadError")}</p>
        </div>
      )}

      {!isLoading && !isError && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[16rem_1fr]">
          <Card className="p-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">{t("menuAdmin.categories")}</p>
              <button
                type="button"
                onClick={() => {
                  setEditingCategoryId(null);
                  setCategoryDialogOpen(true);
                }}
                className="rounded-md p-1 text-brand-600 hover:bg-brand-50 focus-ring"
                aria-label={t("menuAdmin.addCategory")}
              >
                <Plus size={16} />
              </button>
            </div>
            <button
              type="button"
              onClick={() => setSelectedCategoryId(null)}
              className={cn(
                "mb-1 flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-left text-sm font-medium",
                selectedCategoryId === null ? "bg-brand-50 text-brand-700" : "text-stone-600 hover:bg-stone-50"
              )}
            >
              {t("pos.allCategories")}
            </button>
            {(categories ?? []).map((category) => (
              <div
                key={category.id}
                className={cn(
                  "group mb-1 flex items-center justify-between rounded-lg px-2.5 py-2 text-sm font-medium",
                  selectedCategoryId === category.id ? "bg-brand-50 text-brand-700" : "text-stone-600 hover:bg-stone-50"
                )}
              >
                <button type="button" onClick={() => setSelectedCategoryId(category.id)} className="flex-1 text-left">
                  {category.name}
                  {!category.is_active && <span className="ml-1.5 text-[10px] text-stone-400">({t("menuAdmin.inactive")})</span>}
                </button>
                <span className="hidden items-center gap-0.5 group-hover:flex">
                  <button
                    type="button"
                    onClick={() => {
                      setEditingCategoryId(category.id);
                      setCategoryDialogOpen(true);
                    }}
                    className="rounded p-1 text-stone-400 hover:bg-white hover:text-stone-700"
                    aria-label={t("common.save")}
                  >
                    <Pencil size={12} />
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleDeleteCategory(category)}
                    className="rounded p-1 text-stone-400 hover:bg-white hover:text-danger-600"
                    aria-label={t("menuAdmin.deleteCategory")}
                  >
                    <Trash2 size={12} />
                  </button>
                </span>
              </div>
            ))}
            {(categories ?? []).length === 0 && <p className="px-2.5 py-2 text-xs text-stone-400">{t("menuAdmin.noCategories")}</p>}
          </Card>

          <div>
            {visibleItems.length === 0 ? (
              <Card className="flex flex-col items-center justify-center gap-2 p-16 text-center text-stone-400">
                <p className="text-sm">{t("menuAdmin.noItems")}</p>
              </Card>
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {visibleItems.map((item) => (
                  <Card
                    key={item.id}
                    className={cn("cursor-pointer p-4 transition-shadow hover:shadow-popover", !item.is_active && "opacity-60")}
                    onClick={() => {
                      setEditingItemId(item.id);
                      setItemDialogOpen(true);
                    }}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <VegIndicator isVeg={item.is_veg} />
                        <span className="text-sm font-semibold text-stone-800">{item.name}</span>
                      </div>
                      <Pencil size={13} className="mt-0.5 shrink-0 text-stone-300" />
                    </div>
                    <p className="mt-1.5 text-sm font-bold text-stone-900">{formatCurrency(item.base_price)}</p>
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {!item.is_active && <span className="rounded-full bg-stone-100 px-1.5 py-0.5 text-[10px] text-stone-500">{t("menuAdmin.inactive")}</span>}
                      {item.is_sold_out && <span className="rounded-full bg-danger-50 px-1.5 py-0.5 text-[10px] text-danger-600">{t("pos.soldOut")}</span>}
                      {item.is_todays_special && <span className="rounded-full bg-accent-50 px-1.5 py-0.5 text-[10px] text-accent-600">{t("pos.special")}</span>}
                      {item.variants.length > 0 && (
                        <span className="rounded-full bg-stone-100 px-1.5 py-0.5 text-[10px] text-stone-500">
                          {t("menuAdmin.variantCount", { count: item.variants.length })}
                        </span>
                      )}
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <CategoryFormDialog open={categoryDialogOpen} category={editingCategory} onClose={() => setCategoryDialogOpen(false)} />
      <MenuItemDialog
        open={itemDialogOpen}
        item={editingItem}
        categories={categories ?? []}
        defaultCategoryId={selectedCategoryId ?? undefined}
        onClose={() => setItemDialogOpen(false)}
      />
    </div>
  );
}
