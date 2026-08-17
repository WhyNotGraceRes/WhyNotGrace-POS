import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { websiteApi } from "@/api/website";

export function usePublicWebsite(businessSlug: string | undefined) {
  return useQuery({
    queryKey: ["website", "public", businessSlug],
    queryFn: ({ signal }) => websiteApi.getSite(businessSlug as string, signal),
    enabled: Boolean(businessSlug),
    retry: false,
    staleTime: 60_000,
  });
}

export function usePublicWebsiteMenu(businessSlug: string | undefined) {
  const { i18n } = useTranslation();
  const lang = i18n.resolvedLanguage ?? "en";
  return useQuery({
    queryKey: ["website", "public", businessSlug, "menu", lang],
    queryFn: ({ signal }) => websiteApi.getMenu(businessSlug as string, lang, signal),
    enabled: Boolean(businessSlug),
    staleTime: 60_000,
  });
}
