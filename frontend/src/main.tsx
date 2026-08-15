import { StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";

import "@/index.css";
import "@/i18n";
import { queryClient } from "@/lib/queryClient";
import { App } from "@/App";
import { FullPageSpinner } from "@/components/FullPageSpinner";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Suspense fallback={<FullPageSpinner />}>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </Suspense>
  </StrictMode>
);
