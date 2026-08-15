import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { staffApi } from "@/api/staff";
import type { StaffCreateRequest, StaffUpdateRequest } from "@/types/models";

export function useStaff() {
  return useQuery({
    queryKey: ["staff"],
    queryFn: ({ signal }) => staffApi.list(signal),
    staleTime: 30_000,
  });
}

function useInvalidateStaff() {
  const queryClient = useQueryClient();
  return () => void queryClient.invalidateQueries({ queryKey: ["staff"] });
}

export function useCreateStaff() {
  const invalidate = useInvalidateStaff();
  return useMutation({
    mutationFn: (payload: StaffCreateRequest) => staffApi.create(payload),
    onSuccess: invalidate,
  });
}

export function useUpdateStaff() {
  const invalidate = useInvalidateStaff();
  return useMutation({
    mutationFn: ({ staffId, payload }: { staffId: string; payload: StaffUpdateRequest }) =>
      staffApi.update(staffId, payload),
    onSuccess: invalidate,
  });
}

export function useResetStaffAccess() {
  const invalidate = useInvalidateStaff();
  return useMutation({
    mutationFn: (staffId: string) => staffApi.resetAccess(staffId),
    onSuccess: invalidate,
  });
}
