import { useTranslation } from "react-i18next";
import { cn } from "@/lib/cn";
import type { MenuCategoryOut } from "@/types/models";

export function CategoryTabs({
  categories,
  selectedId,
  onSelect,
}: {
  categories: MenuCategoryOut[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}) {
  const { t } = useTranslation();

  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      <button
        type="button"
        onClick={() => onSelect(null)}
        className={cn(
          "shrink-0 rounded-full px-4 py-1.5 text-sm font-semibold transition-colors focus-ring",
          selectedId === null ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
        )}
      >
        {t("pos.allCategories")}
      </button>
      {categories.map((category) => (
        <button
          key={category.id}
          type="button"
          onClick={() => onSelect(category.id)}
          className={cn(
            "shrink-0 rounded-full px-4 py-1.5 text-sm font-semibold transition-colors focus-ring",
            selectedId === category.id ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
          )}
        >
          {category.name}
        </button>
      ))}
    </div>
  );
}
