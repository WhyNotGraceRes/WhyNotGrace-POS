import { AxiosError } from "axios";
import type { ValidationError } from "@/types/models";

/**
 * Normalized error shape for the whole app. The backend's `detail` field
 * is either a plain string (typical HTTPException) or an array of
 * {loc, msg, type} objects (FastAPI 422 validation errors) — see
 * backend/app/main.py's validation_exception_handler. Callers should
 * always go through parseApiError rather than reading axios errors directly.
 */
export class ApiError extends Error {
  status: number | null;
  fieldErrors: Record<string, string>;

  constructor(message: string, status: number | null, fieldErrors: Record<string, string> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

function fieldPathToName(loc: ValidationError["loc"]): string {
  // FastAPI locs look like ["body", "email"] — drop the "body"/"query" prefix.
  const parts = loc.filter((p) => p !== "body" && p !== "query" && p !== "path");
  return parts.join(".") || "form";
}

export function parseApiError(error: unknown): ApiError {
  if (error instanceof AxiosError) {
    const status = error.response?.status ?? null;
    const data = error.response?.data as { detail?: unknown } | undefined;
    const detail = data?.detail;

    if (Array.isArray(detail)) {
      const fieldErrors: Record<string, string> = {};
      for (const item of detail as ValidationError[]) {
        fieldErrors[fieldPathToName(item.loc)] = item.msg;
      }
      const message = detail[0]?.msg ?? "Please check the form and try again.";
      return new ApiError(message, status, fieldErrors);
    }

    if (typeof detail === "string") {
      return new ApiError(detail, status);
    }

    if (error.code === "ERR_CANCELED") {
      return new ApiError("Request cancelled", null);
    }

    if (!error.response) {
      return new ApiError("Could not reach the server. Check your connection and try again.", null);
    }

    return new ApiError(`Something went wrong (${status}).`, status);
  }

  if (error instanceof Error) {
    return new ApiError(error.message, null);
  }

  return new ApiError("An unexpected error occurred.", null);
}
