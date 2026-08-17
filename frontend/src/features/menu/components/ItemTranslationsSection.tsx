import { useItemTranslations, useSetItemTranslation } from "@/features/menu/hooks";
import { TranslationsEditor } from "@/features/menu/components/TranslationsEditor";
import type { MenuItemOut } from "@/types/models";

export function ItemTranslationsSection({ item }: { item: MenuItemOut }) {
  const { data: translations, isLoading } = useItemTranslations(item.id);
  const setTranslation = useSetItemTranslation(item.id);

  return (
    <TranslationsEditor
      englishName={item.name}
      englishDescription={item.description ?? ""}
      translations={translations}
      isLoading={isLoading}
      isSaving={setTranslation.isPending}
      onSave={(language, payload) => setTranslation.mutateAsync({ language, payload })}
    />
  );
}
