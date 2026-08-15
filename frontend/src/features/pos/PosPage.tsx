import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle } from "lucide-react";

import { Spinner } from "@/components/ui/Spinner";
import { Dialog } from "@/components/ui/Dialog";
import { formatCurrency } from "@/lib/format";
import { useCategories, useMenuItems } from "@/features/menu/hooks";
import { cartEstimatedSubtotal, useCartStore } from "@/stores/cartStore";
import { CategoryTabs } from "@/features/pos/components/CategoryTabs";
import { MenuSearch } from "@/features/pos/components/MenuSearch";
import { MenuItemCard } from "@/features/pos/components/MenuItemCard";
import { ItemCustomizeDialog } from "@/features/pos/components/ItemCustomizeDialog";
import { CartPanel } from "@/features/pos/components/CartPanel";
import { OrderSuccessDialog } from "@/features/pos/components/OrderSuccessDialog";
import type { MenuItemOut, OrderOut } from "@/types/models";

export function PosPage() {
  const { t } = useTranslation();
  const { data: categories, isLoading: categoriesLoading, isError: categoriesError } = useCategories();
  const { data: items, isLoading: itemsLoading, isError: itemsError } = useMenuItems();
  const addLine = useCartStore((s) => s.addLine);
  const lines = useCartStore((s) => s.lines);

  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [customizingItem, setCustomizingItem] = useState<MenuItemOut | null>(null);
  const [confirmedOrder, setConfirmedOrder] = useState<OrderOut | null>(null);
  const [mobileCartOpen, setMobileCartOpen] = useState(false);

  const visibleItems = useMemo(() => {
    if (!items) return [];
    const query = search.trim().toLowerCase();
    return items
      .filter((item) => item.is_active)
      .filter((item) => !selectedCategoryId || item.category_id === selectedCategoryId)
      .filter((item) => !query || item.name.toLowerCase().includes(query));
  }, [items, selectedCategoryId, search]);

  const handleSelectItem = (item: MenuItemOut) => {
    const isSimple = item.variants.length === 0 && item.option_groups.length === 0;
    if (!isSimple) {
      setCustomizingItem(item);
      return;
    }
    const existing = lines.find(
      (l) => l.menuItemId === item.id && !l.variantId && l.options.length === 0 && !l.specialInstructions
    );
    if (existing) {
      useCartStore.getState().setQuantity(existing.id, existing.quantity + 1);
    } else {
      addLine({
        menuItemId: item.id,
        itemName: item.name,
        isVeg: item.is_veg,
        unitEstimate: item.base_price,
        options: [],
        quantity: 1,
      });
    }
  };

  const isLoading = categoriesLoading || itemsLoading;
  const isError = categoriesError || itemsError;

  return (
    <div className="flex h-[calc(100vh-6.5rem)] gap-4 lg:h-[calc(100vh-5.5rem)]">
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        <MenuSearch value={search} onChange={setSearch} />

        {categories && categories.length > 0 && (
          <CategoryTabs categories={categories} selectedId={selectedCategoryId} onSelect={setSelectedCategoryId} />
        )}

        <div className="flex-1 overflow-y-auto rounded-card border border-slate-200 bg-white p-3">
          {isLoading && (
            <div className="flex h-full items-center justify-center">
              <Spinner className="text-brand-600" />
            </div>
          )}

          {isError && (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-danger-600">
              <AlertTriangle size={22} />
              <p className="text-sm font-medium">{t("pos.menuLoadError")}</p>
            </div>
          )}

          {!isLoading && !isError && visibleItems.length === 0 && (
            <div className="flex h-full items-center justify-center text-center text-sm text-slate-400">
              {search ? t("pos.noSearchResults", { query: search }) : t("pos.noItems")}
            </div>
          )}

          {!isLoading && !isError && visibleItems.length > 0 && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
              {visibleItems.map((item) => (
                <MenuItemCard key={item.id} item={item} onSelect={handleSelectItem} />
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="hidden w-80 shrink-0 rounded-card border border-slate-200 bg-white sm:block xl:w-96">
        <CartPanel onOrderPlaced={setConfirmedOrder} />
      </div>

      {/* Cart becomes a bottom sheet below the sm breakpoint so it's never
          squeezed off-screen on a phone-sized viewport. */}
      {lines.length > 0 && (
        <button
          type="button"
          onClick={() => setMobileCartOpen(true)}
          className="fixed inset-x-4 bottom-4 z-30 flex items-center justify-between rounded-lg bg-brand-600 px-4 py-3 text-sm font-semibold text-white shadow-popover sm:hidden"
        >
          <span>{t("pos.viewCart", { count: lines.reduce((s, l) => s + l.quantity, 0) })}</span>
          <span>{formatCurrency(cartEstimatedSubtotal(lines))}</span>
        </button>
      )}
      <Dialog open={mobileCartOpen} onClose={() => setMobileCartOpen(false)} title={t("pos.currentOrder")} size="sm">
        <div className="-m-5 h-[70vh]">
          <CartPanel
            onOrderPlaced={(order) => {
              setMobileCartOpen(false);
              setConfirmedOrder(order);
            }}
          />
        </div>
      </Dialog>

      <ItemCustomizeDialog item={customizingItem} onClose={() => setCustomizingItem(null)} />
      <OrderSuccessDialog order={confirmedOrder} onClose={() => setConfirmedOrder(null)} />
    </div>
  );
}
