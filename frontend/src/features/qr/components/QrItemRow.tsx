import { useTranslation } from "react-i18next";
import { VegIndicator } from "@/components/VegIndicator";
import { formatCurrency } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { QRMenuItemOut } from "@/types/models";

export function QrItemRow({ item, onSelect }: { item: QRMenuItemOut; onSelect: (item: QRMenuItemOut) => void }) {
  const { t } = useTranslation();
  const hasVariants = item.variants.length > 0;
  const lowestVariantDelta = hasVariants ? Math.min(...item.variants.map((v) => v.price_delta)) : 0;
  const displayPrice = item.price + lowestVariantDelta;

  return (
    <button
      type="button"
      onClick={() => onSelect(item)}
      disabled={item.is_sold_out}
      className={cn(
        "flex w-full items-start gap-3 border-b border-stone-100 px-4 py-4 text-left transition-colors last:border-b-0",
        item.is_sold_out ? "cursor-not-allowed opacity-50" : "active:bg-stone-50"
      )}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <VegIndicator isVeg={item.is_veg} />
          {item.is_todays_special && (
            <span className="rounded-full bg-accent-500 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-white">
              {t("pos.special")}
            </span>
          )}
        </div>
        <p className="mt-1 text-sm font-semibold leading-snug text-stone-900">{item.name}</p>
        {item.description && <p className="mt-0.5 line-clamp-2 text-xs text-stone-500">{item.description}</p>}
        <p className="mt-1.5 text-sm font-bold text-stone-800">
          {hasVariants && lowestVariantDelta !== 0 ? `${t("pos.from")} ` : ""}
          {formatCurrency(displayPrice)}
        </p>
        {item.is_sold_out && (
          <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-stone-400">{t("pos.soldOut")}</p>
        )}
      </div>

      <div className="relative shrink-0">
        {item.image_url ? (
          <img
            src={item.image_url}
            alt={item.name}
            className="h-20 w-20 rounded-lg object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-20 w-20 items-center justify-center rounded-lg bg-stone-100 text-xl font-bold text-stone-300">
            {item.name[0]}
          </div>
        )}
        {!item.is_sold_out && (
          <span className="absolute -bottom-2 left-1/2 -transtone-x-1/2 rounded-md border border-brand-200 bg-white px-2.5 py-0.5 text-xs font-bold text-brand-600 shadow-sm">
            {t("qr.add")}
          </span>
        )}
      </div>
    </button>
  );
}
