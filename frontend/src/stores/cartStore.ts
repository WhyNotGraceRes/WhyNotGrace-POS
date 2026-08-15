import { create } from "zustand";
import type { OrderSource } from "@/types/models";

export interface CartLineOption {
  id: string;
  name: string;
  priceDelta: number;
}

export interface CartLine {
  id: string;
  menuItemId: string;
  itemName: string;
  isVeg: boolean;
  /** Estimate only, computed client-side from real base_price/variant/option
   * deltas already returned by GET /menu/items — for display before the
   * order exists. It is NEVER sent to the backend (OrderItemCreate has no
   * price field) and is superseded by the server-confirmed unit_price /
   * line_total on the OrderOut returned from POST /orders. */
  unitEstimate: number;
  variantId?: string;
  variantName?: string;
  options: CartLineOption[];
  quantity: number;
  specialInstructions?: string;
}

/** Which kind of order the cart is being built for. TABLE/ROOM orders use
 * `tableId`/`tableName` as the (generic) target location — a room is just
 * a Location like any other, per the backend's unified location model. */
export type OrderContext = Extract<OrderSource, "DINE_IN" | "ROOM_SERVICE" | "PICKUP" | "DELIVERY">;

interface CartState {
  orderContext: OrderContext;
  tableId: string | null;
  tableName: string | null;
  deliveryAddress: string;
  /** Optional — OrderCreateRequest.customer_id is genuinely optional on
   * the backend, never required. */
  customerId: string | null;
  customerLabel: string | null;
  lines: CartLine[];
  setOrderContext: (context: OrderContext) => void;
  setTable: (id: string, name: string) => void;
  clearTable: () => void;
  setDeliveryAddress: (address: string) => void;
  setCustomer: (id: string, label: string) => void;
  clearCustomer: () => void;
  addLine: (line: Omit<CartLine, "id">) => void;
  setQuantity: (id: string, quantity: number) => void;
  removeLine: (id: string) => void;
  clearCart: () => void;
}

export const useCartStore = create<CartState>()((set) => ({
  orderContext: "DINE_IN",
  tableId: null,
  tableName: null,
  deliveryAddress: "",
  customerId: null,
  customerLabel: null,
  lines: [],

  // Switching context clears the location — a table doesn't carry over to
  // room service, and neither carries into pickup/delivery.
  setOrderContext: (context) => set({ orderContext: context, tableId: null, tableName: null }),

  setTable: (id, name) => set({ tableId: id, tableName: name }),
  clearTable: () => set({ tableId: null, tableName: null }),

  setDeliveryAddress: (address) => set({ deliveryAddress: address }),

  setCustomer: (id, label) => set({ customerId: id, customerLabel: label }),
  clearCustomer: () => set({ customerId: null, customerLabel: null }),

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

  clearCart: () => set({ lines: [], customerId: null, customerLabel: null, deliveryAddress: "" }),
}));

export function cartEstimatedSubtotal(lines: CartLine[]): number {
  return lines.reduce((sum, line) => {
    const optionsTotal = line.options.reduce((s, o) => s + o.priceDelta, 0);
    return sum + (line.unitEstimate + optionsTotal) * line.quantity;
  }, 0);
}
