import { QueryClient } from "@tanstack/react-query";
import { parseApiError } from "@/api/errors";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        const apiError = parseApiError(error);
        // Never retry auth/permission/validation/not-found errors — only
        // transient network/server failures are worth a retry.
        if (apiError.status && [400, 401, 403, 404, 409, 422].includes(apiError.status)) {
          return false;
        }
        return failureCount < 2;
      },
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
});
