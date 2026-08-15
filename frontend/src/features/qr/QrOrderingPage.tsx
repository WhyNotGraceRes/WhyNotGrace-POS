import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { AlertTriangle, ShoppingCart } from "lucide-react";

import { Spinner } from "@/components/ui/Spinner";
import { formatCurrency } from "@/lib/format";
import { useQrSessionBootstrap } from "@/features/qr/useQrSession";
import { useQrMenu } from "@/features/qr/hooks";
import { useQrSessionStore } from "@/stores/qrSessionStore";
import { qrCartEstimatedSubtotal, useQrCartStore } from "@/stores/qrCartStore";
import { QrItemRow } from "@/features/qr/components/QrItemRow";
import { QrItemDialog } from "@/features/qr/components/QrItemDialog";
import { QrCartSheet } from "@/features/qr/components/QrCartSheet";
import { MenuSearch } from "@/features/pos/components/MenuSearch";
import { cn } from "@/lib/cn";
import type { OrderOut, QRMenuItemOut } from "@/types/models";

export function QrOrderingPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { businessSlug = "", kind = "table", locationId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const code = searchParams.get("c");

  const { status, errorMessage } = useQrSessionBootstrap(businessSlug, locationId, code);
  const sessionToken = useQrSessionStore((s) => s.sessionToken);

  const { data: menu, isLoading: menuLoading, isError: menuError } = useQrMenu(
    sessionToken,
    i18n.resolvedLanguage ?? "en"
  );

  const { lines, addLine, setQuantity } = useQrCartStore();
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [customizingItem, setCustomizingItem] = useState<QRMenuItemOut | null>(null);
  const [cartOpen, setCartOpen] = useState(false);

  const handleSelectItem = (item: QRMenuItemOut) => {
    const isSimple = item.variants.length === 0 && item.option_groups.length === 0;
    if (!isSimple) {
      setCustomizingItem(item);
      return;
    }
    const existing = lines.find((l) => l.menuItemId === item.id && !l.variantId && l.options.length === 0 && !l.specialInstructions);
    if (existing) {
      setQuantity(existing.id, existing.quantity + 1);
    } else {
      addLine({ menuItemId: item.id, itemName: item.name, isVeg: item.is_veg, unitEstimate: item.price, options: [], quantity: 1 });
    }
  };

  const visibleCategories = useMemo(() => {
    if (!menu) return [];
    const query = search.trim().toLowerCase();
    return menu.categories
      .filter((c) => !selectedCategoryId || c.id === selectedCategoryId)
      .map((c) => ({ ...c, items: query ? c.items.filter((i) => i.name.toLowerCase().includes(query)) : c.items }));
  }, [menu, selectedCategoryId, search]);

  const hasAnyVisibleItems = visibleCategories.some((c) => c.items.length > 0);

  const handleOrderPlaced = (order: OrderOut) => {
    setCartOpen(false);
    navigate(`/qr/menu/${businessSlug}/${kind}/${locationId}/order/${order.id}`);
  };

  if (status === "loading") {
    return (
      <div className="flex min-h-[70vh] flex-col items-center justify-center gap-3 px-6 text-center">
        <Spinner size={26} className="text-brand-600" />
        <p className="text-sm text-slate-500">{t("qr.loadingSession")}</p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="flex min-h-[70vh] flex-col items-center justify-center gap-3 px-6 text-center">
        <AlertTriangle size={28} className="text-danger-500" />
        <p className="text-base font-semibold text-slate-800">{t("qr.invalidLink")}</p>
        <p className="text-sm text-slate-500">{errorMessage || t("qr.invalidLinkHint")}</p>
      </div>
    );
  }

  return (
    <div className="pb-24">
      {menu && (
        <div className="sticky top-[57px] z-30 space-y-2.5 border-b border-slate-100 bg-white px-4 py-2.5">
          <MenuSearch value={search} onChange={setSearch} placeholder={t("qr.searchPlaceholder")} />
          <div className="flex gap-2 overflow-x-auto">
            <button
              type="button"
              onClick={() => setSelectedCategoryId(null)}
              className={cn(
                "shrink-0 rounded-full px-3.5 py-1.5 text-xs font-semibold transition-colors focus-ring",
                selectedCategoryId === null ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"
              )}
            >
              {t("pos.allCategories")}
            </button>
            {menu.categories.map((category) => (
              <button
                key={category.id}
                type="button"
                onClick={() => setSelectedCategoryId(category.id)}
                className={cn(
                  "shrink-0 rounded-full px-3.5 py-1.5 text-xs font-semibold transition-colors focus-ring",
                  selectedCategoryId === category.id ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"
                )}
              >
                {category.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {menuLoading && (
        <div className="flex min-h-[50vh] items-center justify-center">
          <Spinner size={24} className="text-brand-600" />
        </div>
      )}

      {menuError && (
        <div className="flex min-h-[50vh] flex-col items-center justify-center gap-2 px-6 text-center text-danger-600">
          <AlertTriangle size={22} />
          <p className="text-sm font-medium">{t("qr.menuLoadError")}</p>
        </div>
      )}

      {menu && !hasAnyVisibleItems && (
        <p className="px-6 py-16 text-center text-sm text-slate-400">
          {search ? t("qr.noSearchResults", { query: search }) : t("qr.noItems")}
        </p>
      )}

      {menu &&
        visibleCategories.map(
          (category) =>
            category.items.length > 0 && (
              <div key={category.id}>
                <h2 className="px-4 pt-4 pb-1 text-sm font-bold text-slate-900">{category.name}</h2>
                <div>
                  {category.items.map((item) => (
                    <QrItemRow key={item.id} item={item} onSelect={handleSelectItem} />
                  ))}
                </div>
              </div>
            )
        )}

      {lines.length > 0 && (
        <button
          type="button"
          onClick={() => setCartOpen(true)}
          className="fixed inset-x-4 bottom-4 z-40 mx-auto flex w-[calc(100%-2rem)] max-w-[26rem] items-center justify-between rounded-xl bg-brand-600 px-4 py-3.5 text-sm font-semibold text-white shadow-popover"
        >
          <span className="flex items-center gap-2">
            <ShoppingCart size={16} />
            {t("qr.cart.view", { count: lines.reduce((s, l) => s + l.quantity, 0) })}
          </span>
          <span>{formatCurrency(qrCartEstimatedSubtotal(lines))}</span>
        </button>
      )}

      <QrItemDialog item={customizingItem} onClose={() => setCustomizingItem(null)} />

      {sessionToken && (
        <QrCartSheet
          open={cartOpen}
          onClose={() => setCartOpen(false)}
          sessionToken={sessionToken}
          onOrderPlaced={handleOrderPlaced}
        />
      )}
    </div>
  );
}
