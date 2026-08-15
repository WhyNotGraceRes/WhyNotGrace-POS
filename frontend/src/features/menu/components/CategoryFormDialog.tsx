import { useState } from "react";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";

import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { parseApiError } from "@/api/errors";
import { useCreateCategory, useUpdateCategory } from "@/features/menu/hooks";
import type { MenuCategoryOut } from "@/types/models";

export function CategoryFormDialog({
  open,
  category,
  onClose,
}: {
  open: boolean;
  category: MenuCategoryOut | null;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const createCategory = useCreateCategory();
  const updateCategory = useUpdateCategory();
  const isEdit = Boolean(category);

  const [name, setName] = useState(category?.name ?? "");
  const [description, setDescription] = useState(category?.description ?? "");
  const [displayOrder, setDisplayOrder] = useState(String(category?.display_order ?? 0));
  const [error, setError] = useState<string | null>(null);

  const [openCategoryId, setOpenCategoryId] = useState<string | null>(category?.id ?? null);
  if (open && (category?.id ?? null) !== openCategoryId) {
    setOpenCategoryId(category?.id ?? null);
    setName(category?.name ?? "");
    setDescription(category?.description ?? "");
    setDisplayOrder(String(category?.display_order ?? 0));
    setError(null);
  }

  const isPending = createCategory.isPending || updateCategory.isPending;

  const handleSubmit = async () => {
    setError(null);
    if (!name.trim()) {
      setError(t("menuAdmin.categoryNameRequired"));
      return;
    }
    try {
      if (isEdit && category) {
        await updateCategory.mutateAsync({
          categoryId: category.id,
          payload: { name: name.trim(), description: description.trim() || null, display_order: Number(displayOrder) || 0 },
        });
        toast.success(t("menuAdmin.categoryUpdated"));
      } else {
        await createCategory.mutateAsync({
          name: name.trim(),
          description: description.trim() || undefined,
          display_order: Number(displayOrder) || 0,
        });
        toast.success(t("menuAdmin.categoryCreated"));
      }
      onClose();
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title={isEdit ? t("menuAdmin.editCategory") : t("menuAdmin.addCategory")} size="sm">
      <div className="space-y-3">
        {error && <p className="text-xs text-danger-600">{error}</p>}
        <div>
          <Label htmlFor="cat-name">{t("menuAdmin.name")}</Label>
          <Input id="cat-name" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="cat-desc">{t("menuAdmin.description")}</Label>
          <Input id="cat-desc" value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="cat-order">{t("menuAdmin.displayOrder")}</Label>
          <Input id="cat-order" type="number" value={displayOrder} onChange={(e) => setDisplayOrder(e.target.value)} />
        </div>
        <Button className="w-full" isLoading={isPending} onClick={() => void handleSubmit()}>
          {isEdit ? t("common.save") : t("menuAdmin.addCategory")}
        </Button>
      </div>
    </Dialog>
  );
}
