import { useTranslation } from "react-i18next";
import { VegIndicator } from "@/components/VegIndicator";
import { formatCurrency } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { MenuItemOut } from "@/types/models";

export function MenuItemCard({ item, onSelect }: { item: MenuItemOut; onSelect: (item: MenuItemOut) => void }) {
  const { t } = useTranslation();
  const hasVariants = item.variants.length > 0;
  const lowestVariantDelta = hasVariants ? Math.min(...item.variants.map((v) => v.price_delta)) : 0;
  const displayPrice = item.base_price + lowestVariantDelta;

  return (
    <button
      type="button"
      onClick={() => onSelect(item)}
      disabled={item.is_sold_out}
      className={cn(
        "group relative flex flex-col overflow-hidden rounded-card border border-stone-200 bg-white text-left transition-shadow",
        item.is_sold_out ? "cursor-not-allowed opacity-60" : "hover:shadow-popover focus-ring"
      )}
    >
      {item.image_url ? (
        <img src={item.image_url} alt={item.name} className="h-24 w-full object-cover" loading="lazy" />
      ) : (
        <div className="flex h-24 w-full items-center justify-center bg-stone-100 text-2xl font-bold text-stone-300">
          {item.name[0]}
        </div>
      )}

      {item.is_sold_out && (
        <span className="absolute right-2 top-2 rounded-full bg-stone-900/80 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
          {t("pos.soldOut")}
        </span>
      )}
      {item.is_todays_special && !item.is_sold_out && (
        <span className="absolute right-2 top-2 rounded-full bg-accent-500 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
          {t("pos.special")}
        </span>
      )}

      <div className="flex flex-1 flex-col gap-1 p-3">
        <div className="flex items-start gap-1.5">
          <VegIndicator isVeg={item.is_veg} />
          <span className="line-clamp-2 text-sm font-semibold leading-snug text-stone-800">{item.name}</span>
        </div>
        <div className="mt-auto flex items-center justify-between pt-1">
          <span className="text-sm font-bold text-stone-900">
            {hasVariants && lowestVariantDelta !== 0 ? `${t("pos.from")} ` : ""}
            {formatCurrency(displayPrice)}
          </span>
          {(hasVariants || item.option_groups.length > 0) && (
            <span className="text-[10px] font-medium text-stone-400">{t("pos.customizable")}</span>
          )}
        </div>
      </div>
    </button>
  );
}
