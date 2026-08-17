import { qrClient } from "@/api/qrClient";
import type { PublicWebsiteResponse, QRMenuCategoryOut } from "@/types/models";

/** The public marketing site — same unauthenticated client as QR ordering
 * (see qrClient), since a website visitor is just as anonymous as a
 * table's QR scan. */
export const websiteApi = {
  getSite: async (businessSlug: string, signal?: AbortSignal): Promise<PublicWebsiteResponse> => {
    const { data } = await qrClient.get<PublicWebsiteResponse>(`/website/public/${businessSlug}`, { signal });
    return data;
  },

  getMenu: async (businessSlug: string, lang: string, signal?: AbortSignal): Promise<QRMenuCategoryOut[]> => {
    const { data } = await qrClient.get<QRMenuCategoryOut[]>(`/website/public/${businessSlug}/menu`, {
      params: { language: lang },
      signal,
    });
    return data;
  },
};
