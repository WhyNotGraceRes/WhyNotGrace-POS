import { apiClient } from "@/api/client";
import { normalizeMenuItem } from "@/api/normalize";
import type {
  MenuCategoryCreate,
  MenuCategoryOut,
  MenuCategoryUpdate,
  MenuItemCreate,
  MenuItemOut,
  MenuItemUpdate,
  MenuOptionCreate,
  MenuOptionGroupCreate,
  MenuOptionGroupOut,
  MenuOptionGroupUpdate,
  MenuOptionOut,
  MenuOptionUpdate,
  MenuVariantCreate,
  MenuVariantOut,
  MenuVariantUpdate,
} from "@/types/models";

export const categoriesApi = {
  list: (signal?: AbortSignal) =>
    apiClient.get<MenuCategoryOut[]>("/categories", { signal }).then((r) => r.data),

  create: (payload: MenuCategoryCreate) =>
    apiClient.post<MenuCategoryOut>("/categories", payload).then((r) => r.data),

  update: (categoryId: string, payload: MenuCategoryUpdate) =>
    apiClient.put<MenuCategoryOut>(`/categories/${categoryId}`, payload).then((r) => r.data),

  delete: (categoryId: string) => apiClient.delete(`/categories/${categoryId}`),
};

export const menuApi = {
  listItems: (params: { category_id?: string } = {}, signal?: AbortSignal) =>
    apiClient
      .get<MenuItemOut[]>("/menu/items", { params, signal })
      .then((r) => r.data.map(normalizeMenuItem)),

  createItem: (payload: MenuItemCreate) =>
    apiClient.post<MenuItemOut>("/menu/items", payload).then((r) => normalizeMenuItem(r.data)),

  updateItem: (itemId: string, payload: MenuItemUpdate) =>
    apiClient.put<MenuItemOut>(`/menu/items/${itemId}`, payload).then((r) => normalizeMenuItem(r.data)),

  deleteItem: (itemId: string) => apiClient.delete(`/menu/items/${itemId}`),

  addVariant: (itemId: string, payload: MenuVariantCreate) =>
    apiClient.post<MenuItemOut>(`/menu/items/${itemId}/variants`, payload).then((r) => normalizeMenuItem(r.data)),

  addOptionGroup: (itemId: string, payload: MenuOptionGroupCreate) =>
    apiClient.post<MenuItemOut>(`/menu/items/${itemId}/option-groups`, payload).then((r) => normalizeMenuItem(r.data)),

  addOption: (groupId: string, payload: MenuOptionCreate) =>
    apiClient.post<MenuOptionOut>(`/menu/option-groups/${groupId}/options`, payload).then((r) => r.data),

  updateVariant: (variantId: string, payload: MenuVariantUpdate) =>
    apiClient.put<MenuVariantOut>(`/menu/variants/${variantId}`, payload).then((r) => r.data),

  deleteVariant: (variantId: string) => apiClient.delete(`/menu/variants/${variantId}`),

  updateOptionGroup: (groupId: string, payload: MenuOptionGroupUpdate) =>
    apiClient.put<MenuOptionGroupOut>(`/menu/option-groups/${groupId}`, payload).then((r) => r.data),

  deleteOptionGroup: (groupId: string) => apiClient.delete(`/menu/option-groups/${groupId}`),

  updateOption: (optionId: string, payload: MenuOptionUpdate) =>
    apiClient.put<MenuOptionOut>(`/menu/options/${optionId}`, payload).then((r) => r.data),

  deleteOption: (optionId: string) => apiClient.delete(`/menu/options/${optionId}`),
};
