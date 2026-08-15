import { Search, X } from "lucide-react";
import { useTranslation } from "react-i18next";

export function MenuSearch({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  const { t } = useTranslation();

  return (
    <div className="relative">
      <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder ?? t("pos.searchPlaceholder")}
        className="h-10 w-full rounded-lg border border-slate-300 bg-white pl-9 pr-9 text-sm focus-ring"
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange("")}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-full p-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          aria-label={t("pos.clearSearch")}
        >
          <X size={15} />
        </button>
      )}
    </div>
  );
}
