import { useState } from "react";
import toast from "react-hot-toast";
import { Plus, Trash2, Upload } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Switch } from "@/components/ui/Switch";
import { parseApiError } from "@/api/errors";
import { useExtractMenuFromPhotos, usePublishImportedMenu } from "@/features/platform/hooks";
import type { MenuImportCategoryDraft } from "@/types/models";

export function MenuImportSection({ businessId }: { businessId: string }) {
  const extractMenu = useExtractMenuFromPhotos(businessId);
  const publishMenu = usePublishImportedMenu(businessId);

  const [files, setFiles] = useState<File[]>([]);
  const [draft, setDraft] = useState<MenuImportCategoryDraft[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleExtract = async () => {
    setError(null);
    if (files.length === 0) {
      setError("Choose at least one photo of the menu card.");
      return;
    }
    try {
      const result = await extractMenu.mutateAsync(files);
      setDraft(result.categories);
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const handlePublish = async () => {
    if (!draft) return;
    setError(null);
    try {
      const result = await publishMenu.mutateAsync(draft);
      toast.success(`Published ${result.categories_created} categories, ${result.items_created} items.`);
      setDraft(null);
      setFiles([]);
    } catch (err) {
      setError(parseApiError(err).message);
    }
  };

  const updateCategoryName = (catIndex: number, name: string) => {
    setDraft((prev) => prev?.map((c, i) => (i === catIndex ? { ...c, name } : c)) ?? null);
  };

  const deleteCategory = (catIndex: number) => {
    setDraft((prev) => prev?.filter((_, i) => i !== catIndex) ?? null);
  };

  const addCategory = () => {
    setDraft((prev) => [...(prev ?? []), { name: "New category", items: [] }]);
  };

  const updateItem = (catIndex: number, itemIndex: number, patch: Partial<MenuImportCategoryDraft["items"][number]>) => {
    setDraft(
      (prev) =>
        prev?.map((c, ci) =>
          ci === catIndex ? { ...c, items: c.items.map((it, ii) => (ii === itemIndex ? { ...it, ...patch } : it)) } : c
        ) ?? null
    );
  };

  const deleteItem = (catIndex: number, itemIndex: number) => {
    setDraft(
      (prev) => prev?.map((c, ci) => (ci === catIndex ? { ...c, items: c.items.filter((_, ii) => ii !== itemIndex) } : c)) ??
        null
    );
  };

  const addItem = (catIndex: number) => {
    setDraft(
      (prev) =>
        prev?.map((c, ci) =>
          ci === catIndex ? { ...c, items: [...c.items, { name: "New item", price: 0, is_veg: true }] } : c
        ) ?? null
    );
  };

  const totalItems = draft?.reduce((sum, c) => sum + c.items.length, 0) ?? 0;

  return (
    <div className="space-y-4">
      <p className="text-xs text-stone-500">
        Upload photo(s) of the restaurant's physical menu card — the categories and items are read automatically into
        an editable draft below. Nothing is added to their real menu until you review it and hit publish.
      </p>

      {error && (
        <p className="rounded-lg border border-danger-500/30 bg-danger-50 px-3 py-2 text-xs text-danger-700">{error}</p>
      )}

      {!draft && (
        <div className="space-y-3">
          <label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-stone-300 px-4 py-6 text-sm text-stone-500 hover:border-brand-400 hover:bg-brand-50/40">
            <Upload size={16} />
            {files.length > 0 ? `${files.length} photo(s) selected` : "Choose menu card photo(s)"}
            <input
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            />
          </label>
          <Button size="sm" isLoading={extractMenu.isPending} onClick={() => void handleExtract()}>
            Extract menu
          </Button>
        </div>
      )}

      {draft && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">
              Draft — {draft.length} categories, {totalItems} items
            </p>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setDraft(null);
                setFiles([]);
              }}
            >
              Start over
            </Button>
          </div>

          <div className="space-y-4">
            {draft.map((category, catIndex) => (
              <div key={catIndex} className="rounded-lg border border-stone-200 p-3">
                <div className="mb-2 flex items-center gap-2">
                  <Input
                    value={category.name}
                    onChange={(e) => updateCategoryName(catIndex, e.target.value)}
                    className="font-semibold"
                  />
                  <button
                    type="button"
                    onClick={() => deleteCategory(catIndex)}
                    className="shrink-0 rounded p-1.5 text-stone-400 hover:bg-danger-50 hover:text-danger-600"
                    aria-label="Delete category"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>

                <div className="space-y-2">
                  {category.items.map((item, itemIndex) => (
                    <div key={itemIndex} className="flex flex-wrap items-center gap-2 rounded-lg bg-stone-50 p-2">
                      <Switch
                        checked={item.is_veg}
                        onChange={(checked) => updateItem(catIndex, itemIndex, { is_veg: checked })}
                        label="Vegetarian"
                      />
                      <Input
                        value={item.name}
                        onChange={(e) => updateItem(catIndex, itemIndex, { name: e.target.value })}
                        placeholder="Item name"
                        className="min-w-[9rem] flex-1"
                      />
                      <Input
                        value={item.description ?? ""}
                        onChange={(e) => updateItem(catIndex, itemIndex, { description: e.target.value || null })}
                        placeholder="Description (optional)"
                        className="min-w-[9rem] flex-1"
                      />
                      <Input
                        type="number"
                        min={0.01}
                        step="0.01"
                        value={item.price}
                        onChange={(e) => updateItem(catIndex, itemIndex, { price: Number(e.target.value) || 0 })}
                        className="w-24"
                      />
                      <button
                        type="button"
                        onClick={() => deleteItem(catIndex, itemIndex)}
                        className="shrink-0 rounded p-1.5 text-stone-400 hover:bg-danger-50 hover:text-danger-600"
                        aria-label="Delete item"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  ))}
                  {category.items.length === 0 && <p className="text-xs text-stone-400">No items yet.</p>}
                </div>

                <Button variant="ghost" size="sm" className="mt-2" onClick={() => addItem(catIndex)}>
                  <Plus size={13} /> Add item
                </Button>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" onClick={addCategory}>
              <Plus size={14} /> Add category
            </Button>
            <Button size="sm" isLoading={publishMenu.isPending} onClick={() => void handlePublish()}>
              Publish {totalItems} items to menu
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
