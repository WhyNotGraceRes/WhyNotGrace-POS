import { qrClient } from "@/api/qrClient";
import { normalizeOrder } from "@/api/normalize";
import type { OrderOut, QRMenuResponse, QROrderCreateRequest, QRScanResponse } from "@/types/models";

/** Every menu/order call after scanning is scoped by this session token —
 * never by a business/location/table id supplied directly by the client. */
function sessionHeader(sessionToken: string) {
  return { headers: { "X-QR-Session": sessionToken } };
}

export const qrApi = {
  scan: async (businessSlug: string, locationId: string, code: string, signal?: AbortSignal): Promise<QRScanResponse> => {
    const { data } = await qrClient.get<QRScanResponse>(`/qr/scan/${businessSlug}/${locationId}`, {
      params: { c: code },
      signal,
    });
    return data;
  },

  getMenu: async (sessionToken: string, lang: string, signal?: AbortSignal): Promise<QRMenuResponse> => {
    const { data } = await qrClient.get<QRMenuResponse>("/qr/menu", {
      ...sessionHeader(sessionToken),
      params: { lang },
      signal,
    });
    return data;
  },

  placeOrder: async (sessionToken: string, payload: QROrderCreateRequest): Promise<OrderOut> => {
    const { data } = await qrClient.post<OrderOut>("/qr/orders", payload, sessionHeader(sessionToken));
    return normalizeOrder(data);
  },

  getOrderStatus: async (sessionToken: string, orderId: string, signal?: AbortSignal): Promise<OrderOut> => {
    const { data } = await qrClient.get<OrderOut>(`/qr/orders/${orderId}`, {
      ...sessionHeader(sessionToken),
      signal,
    });
    return normalizeOrder(data);
  },
};
