import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { categoriesApi, menuApi } from "@/api/menu";
import type {
  MenuCategoryCreate,
  MenuCategoryUpdate,
  MenuItemCreate,
  MenuItemUpdate,
  MenuOptionCreate,
  MenuOptionGroupCreate,
  MenuOptionGroupUpdate,
  MenuOptionUpdate,
  MenuVariantCreate,
  MenuVariantUpdate,
} from "@/types/models";

export function useCategories() {
  return useQuery({
    queryKey: ["categories"],
    queryFn: ({ signal }) => categoriesApi.list(signal),
    staleTime: 60_000,
  });
}

export function useMenuItems() {
  return useQuery({
    queryKey: ["menu-items"],
    queryFn: ({ signal }) => menuApi.listItems({}, signal),
    staleTime: 30_000,
  });
}

function useInvalidateMenu() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: ["categories"] });
    void queryClient.invalidateQueries({ queryKey: ["menu-items"] });
  };
}

export function useCreateCategory() {
  const invalidate = useInvalidateMenu();
  return useMutation({
    mutationFn: (payload: MenuCategoryCreate) => categoriesApi.create(payload),
    onSuccess: invalidate,
  });
}

export function useUpdateCategory() {
  const invalidate = useInvalidateMenu();
  return useMutation({
    mutationFn: ({ categoryId, payload }: { categoryId: string; payload: MenuCategoryUpdate }) =>
      categoriesApi.update(categoryId, payload),
    onSuccess: invalidate,
  });
}

export function useDeleteCategory() {
  const invalidate = useInvalidateMenu();
  return useMutation({
    mutationFn: (categoryId: string) => categoriesApi.delete(categoryId),
    onSuccess: invalidate,
  });
}

export function useCreateMenuItem() {
  const invalidate = useInvalidateMenu();
  return useMutation({
    mutationFn: (payload: MenuItemCreate) => menuApi.createItem(payload),
    onSuccess: invalidate,
  });
}

export function useUpdateMenuItem() {
  const invalidate = useInvalidateMenu();
  return useMutation({
    mutationFn: ({ itemId, payload }: { itemId: string; payload: MenuItemUpdate }) =>
      menuApi.updateItem(itemId, payload),
    onSuccess: invalidate,
  });
}

export function useDeleteMenuItem() {
  const invalidate = useInvalidateMenu();
  return useMutation({
    mutationFn: (itemId: string) => menuApi.deleteItem(itemId),
    onSuccess: invalidate,
  });
}

export function useAddVariant() {
  const invalidate = useInvalidateMenu();
  return useMutation({
    mutationFn: ({ itemId, payload }: { itemId: string; payload: MenuVariantCreate }) =>
      menuApi.addVariant(itemId, payload),
    onSuccess: invalidate,
  });
}

export function useAddOptionGroup() {
  const invalidate = useInvalidateMenu();
  return useMutation({
    mutationFn: ({ itemId, payload }: { itemId: string; payload: MenuOptionGroupCreate }) =>
      menuApi.addOptionGroup(itemId, payload),
    onSuccess: invalidate,
  });
}

export function useAddOption() {
  const invalidate = useInvalidateMenu();
  return useMutation({
    mutationFn: ({ groupId, payload }: { groupId: string; payload: MenuOptionCreate }) =>
      menuApi.addOption(groupId, payload),
    onSuccess: invalidate,
  });
}

export function useUpdateVariant() {
  const invalidate = useInvalidateMenu();
  return useMutation({
    mutationFn: ({ variantId, payload }: { variantId: string; payload: MenuVariantUpdate }) =>
      menuApi.updateVariant(variantId, payload),
    onSuccess: invalidate,
  });
}

export function useDeleteVariant() {
  const invalidate = useInvalidateMenu();
  return useMutation({
    mutationFn: (variantId: string) => menuApi.deleteVariant(variantId),
    onSuccess: invalidate,
  });
}

export function useUpdateOptionGroup() {
  const invalidate = useInvalidateMenu();
  return useMutation({
    mutationFn: ({ groupId, payload }: { groupId: string; payload: MenuOptionGroupUpdate }) =>
      menuApi.updateOptionGroup(groupId, payload),
    onSuccess: invalidate,
  });
}

export function useDeleteOptionGroup() {
  const invalidate = useInvalidateMenu();
  return useMutation({
    mutationFn: (groupId: string) => menuApi.deleteOptionGroup(groupId),
    onSuccess: invalidate,
  });
}

export function useUpdateOption() {
  const invalidate = useInvalidateMenu();
  return useMutation({
    mutationFn: ({ optionId, payload }: { optionId: string; payload: MenuOptionUpdate }) =>
      menuApi.updateOption(optionId, payload),
    onSuccess: invalidate,
  });
}

export function useDeleteOption() {
  const invalidate = useInvalidateMenu();
  return useMutation({
    mutationFn: (optionId: string) => menuApi.deleteOption(optionId),
    onSuccess: invalidate,
  });
}
