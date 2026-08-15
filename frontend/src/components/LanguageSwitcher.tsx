import { useTranslation } from "react-i18next";
import { SUPPORTED_LANGUAGES } from "@/i18n";
import { cn } from "@/lib/cn";

export function LanguageSwitcher({ className }: { className?: string }) {
  const { i18n } = useTranslation();

  return (
    <div className={cn("inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white p-1", className)}>
      {SUPPORTED_LANGUAGES.map((lang) => (
        <button
          key={lang.code}
          type="button"
          onClick={() => void i18n.changeLanguage(lang.code)}
          className={cn(
            "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
            i18n.resolvedLanguage === lang.code
              ? "bg-brand-600 text-white"
              : "text-slate-600 hover:bg-slate-100"
          )}
        >
          {lang.label}
        </button>
      ))}
    </div>
  );
}
