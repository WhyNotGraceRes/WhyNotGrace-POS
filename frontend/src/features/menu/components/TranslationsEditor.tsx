import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { Languages } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { parseApiError } from "@/api/errors";
import { cn } from "@/lib/cn";
import { SUPPORTED_LANGUAGES } from "@/i18n";
import type { TranslationOut } from "@/types/models";

const TRANSLATABLE_LANGUAGES = SUPPORTED_LANGUAGES.filter((lang) => lang.code !== "en");

/** Shared by ItemTranslationsSection and CategoryTranslationsSection — the
 * per-language name/description form, a language tab strip, and a save
 * button. Purely presentational: data fetching and the actual save call
 * live in the two wrapper components, since items and categories use
 * different hooks/endpoints underneath. */
export function TranslationsEditor({
  englishName,
  englishDescription,
  translations,
  isLoading,
  isSaving,
  onSave,
}: {
  englishName: string;
  /** Omit entirely to hide the description field (categories have none). */
  englishDescription?: string;
  translations: TranslationOut[] | undefined;
  isLoading: boolean;
  isSaving: boolean;
  onSave: (language: string, payload: { name: string; description?: string }) => Promise<unknown>;
}) {
  const { t } = useTranslation();
  const hasDescriptionField = englishDescription !== undefined;

  const [activeLanguage, setActiveLanguage] = useState<string>(TRANSLATABLE_LANGUAGES[0].code);
  const [drafts, setDrafts] = useState<Record<string, { name: string; description: string }>>({});
  const [error, setError] = useState<string | null>(null);

  const savedRow = translations?.find((row) => row.language === activeLanguage);
  const draft = drafts[activeLanguage];
  const name = draft?.name ?? savedRow?.name ?? "";
  const description = draft?.description ?? savedRow?.description ?? "";

  const setDraftField = (field: "name" | "description", value: string) => {
    setDrafts((prev) => ({
      ...prev,
      [activeLanguage]: {
        name: field === "name" ? value : (prev[activeLanguage]?.name ?? savedRow?.name ?? ""),
        description:
          field === "description" ? value : (prev[activeLanguage]?.description ?? savedRow?.description ?? ""),
      },
    }));
  };

  const handleSave = async () => {
    setError(null);
    try {
      await onSave(activeLanguage, hasDescriptionField ? { name, description } : { name });
      setDrafts((prev) => {
        const next = { ...prev };
        delete next[activeLanguage];
        return next;
      });
      toast.success(t("menuAdmin.translationSaved"));
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  return (
    <div className="rounded-lg border border-stone-200 p-3">
      <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-stone-500">
        <Languages size={13} /> {t("menuAdmin.translations")}
      </p>

      <div className="mb-3 flex gap-1.5">
        {TRANSLATABLE_LANGUAGES.map((lang) => {
          const hasSavedValue = Boolean(translations?.find((row) => row.language === lang.code)?.name);
          const isActive = activeLanguage === lang.code;
          return (
            <button
              key={lang.code}
              type="button"
              onClick={() => setActiveLanguage(lang.code)}
              className={cn(
                "flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium",
                isActive ? "bg-brand-600 text-white" : "bg-stone-100 text-stone-600 hover:bg-stone-200"
              )}
            >
              {lang.label}
              {hasSavedValue && (
                <span className={cn("h-1.5 w-1.5 rounded-full", isActive ? "bg-white" : "bg-brand-500")} />
              )}
            </button>
          );
        })}
      </div>

      {error && <p className="mb-2 text-xs text-danger-600">{error}</p>}

      {isLoading ? (
        <p className="text-xs text-stone-400">{t("common.loading")}</p>
      ) : (
        <div className="space-y-3">
          <div>
            <Label htmlFor="translation-name">{t("menuAdmin.name")}</Label>
            <p className="mb-1 truncate text-xs text-stone-400">
              {t("menuAdmin.translationEnglishReference", { value: englishName })}
            </p>
            <Input
              id="translation-name"
              value={name}
              onChange={(e) => setDraftField("name", e.target.value)}
              placeholder={englishName}
            />
          </div>
          {hasDescriptionField && (
            <div>
              <Label htmlFor="translation-desc">{t("menuAdmin.description")}</Label>
              {englishDescription && (
                <p className="mb-1 line-clamp-1 text-xs text-stone-400">
                  {t("menuAdmin.translationEnglishReference", { value: englishDescription })}
                </p>
              )}
              <Input
                id="translation-desc"
                value={description}
                onChange={(e) => setDraftField("description", e.target.value)}
                placeholder={englishDescription ?? ""}
              />
            </div>
          )}
          <Button type="button" variant="secondary" size="sm" isLoading={isSaving} onClick={() => void handleSave()}>
            {t("menuAdmin.saveTranslation")}
          </Button>
        </div>
      )}
    </div>
  );
}
