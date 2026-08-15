const apiUrl = import.meta.env.VITE_API_URL as string | undefined;

if (!apiUrl) {
  // Fail loudly at startup rather than silently calling the wrong host.
  throw new Error(
    "VITE_API_URL is not set. Copy .env.example to .env and point it at the backend."
  );
}

export const env = {
  apiUrl: apiUrl.replace(/\/+$/, ""),
} as const;
