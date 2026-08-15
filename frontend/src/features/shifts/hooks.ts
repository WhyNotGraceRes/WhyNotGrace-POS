import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { shiftsApi } from "@/api/shifts";
import type { CloseShiftRequest } from "@/types/models";

export function useCurrentShift() {
  return useQuery({
    queryKey: ["shift-current"],
    queryFn: ({ signal }) => shiftsApi.current(signal),
    // Short, because whether a drawer is open changes what the counter can
    // do — a stale answer here means offering Close on a shift somebody
    // already closed on another terminal.
    staleTime: 5_000,
  });
}

export function useShiftReport(shiftId: string | null) {
  return useQuery({
    queryKey: ["shift-report", shiftId],
    queryFn: ({ signal }) => shiftsApi.report(shiftId as string, signal),
    enabled: !!shiftId,
    staleTime: 5_000,
  });
}

export function useShifts() {
  return useQuery({
    queryKey: ["shifts"],
    queryFn: ({ signal }) => shiftsApi.list(signal),
    staleTime: 30_000,
  });
}

export function useOpenShift() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (openingFloat: number) => shiftsApi.open(openingFloat),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["shift-current"] });
      void queryClient.invalidateQueries({ queryKey: ["shifts"] });
    },
  });
}

export function useCloseShift() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ shiftId, payload }: { shiftId: string; payload: CloseShiftRequest }) =>
      shiftsApi.close(shiftId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["shift-current"] });
      void queryClient.invalidateQueries({ queryKey: ["shifts"] });
      void queryClient.invalidateQueries({ queryKey: ["shift-report"] });
    },
  });
}
