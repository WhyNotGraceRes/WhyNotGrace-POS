import { useCategoryTranslations, useSetCategoryTranslation } from "@/features/menu/hooks";
import { TranslationsEditor } from "@/features/menu/components/TranslationsEditor";
import type { MenuCategoryOut } from "@/types/models";

export function CategoryTranslationsSection({ category }: { category: MenuCategoryOut }) {
  const { data: translations, isLoading } = useCategoryTranslations(category.id);
  const setTranslation = useSetCategoryTranslation(category.id);

  return (
    <TranslationsEditor
      englishName={category.name}
      translations={translations}
      isLoading={isLoading}
      isSaving={setTranslation.isPending}
      onSave={(language, payload) => setTranslation.mutateAsync({ language, payload: { name: payload.name } })}
    />
  );
}
