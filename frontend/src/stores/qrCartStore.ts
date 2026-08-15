import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export interface QrCartLineOption {
  id: string;
  name: string;
  priceDelta: number;
}

export interface QrCartLine {
  id: string;
  menuItemId: string;
  itemName: string;
  isVeg: boolean;
  /** Estimate only, computed client-side from the real price/variant/option
   * deltas already returned by GET /qr/menu — for display before the order
   * exists. Never sent to the backend (QRCartItem carries no price field)
   * and is superseded by the server-confirmed unit_price/line_total on the
   * OrderOut returned from POST /qr/orders. */
  unitEstimate: number;
  variantId?: string;
  variantName?: string;
  options: QrCartLineOption[];
  quantity: number;
  specialInstructions?: string;
}

interface QrCartState {
  lines: QrCartLine[];
  addLine: (line: Omit<QrCartLine, "id">) => void;
  setQuantity: (id: string, quantity: number) => void;
  removeLine: (id: string) => void;
  clearCart: () => void;
}

export const useQrCartStore = create<QrCartState>()(
  persist(
    (set) => ({
      lines: [],

      addLine: (line) =>
        set((state) => ({
          lines: [...state.lines, { ...line, id: crypto.randomUUID() }],
        })),

      setQuantity: (id, quantity) =>
        set((state) => ({
          lines:
            quantity <= 0
              ? state.lines.filter((l) => l.id !== id)
              : state.lines.map((l) => (l.id === id ? { ...l, quantity } : l)),
        })),

      removeLine: (id) => set((state) => ({ lines: state.lines.filter((l) => l.id !== id) })),

      clearCart: () => set({ lines: [] }),
    }),
    {
      name: "whynotgrace-qr-cart",
      storage: createJSONStorage(() => sessionStorage),
    }
  )
);

export function qrCartEstimatedSubtotal(lines: QrCartLine[]): number {
  return lines.reduce((sum, line) => {
    const optionsTotal = line.options.reduce((s, o) => s + o.priceDelta, 0);
    return sum + (line.unitEstimate + optionsTotal) * line.quantity;
  }, 0);
}
