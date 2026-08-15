/** Loads Razorpay's hosted Checkout.js widget on demand (never in
 * index.html globally — nothing else on the site needs it, and it's
 * third-party script best kept out of pages that don't use it).
 * Resolves to the global `Razorpay` constructor Checkout.js attaches to
 * `window`. See https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/integration-steps/
 */

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayCheckoutOptions) => { open: () => void };
  }
}

export interface RazorpayCheckoutOptions {
  key: string;
  amount: number;
  currency: string;
  order_id: string;
  name: string;
  description?: string;
  handler: (response: {
    razorpay_payment_id: string;
    razorpay_order_id: string;
    razorpay_signature: string;
  }) => void;
  modal?: { ondismiss?: () => void };
  theme?: { color?: string };
}

const CHECKOUT_SRC = "https://checkout.razorpay.com/v1/checkout.js";

let loadPromise: Promise<void> | null = null;

export function loadRazorpayCheckout(): Promise<void> {
  if (window.Razorpay) return Promise.resolve();
  if (loadPromise) return loadPromise;

  loadPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = CHECKOUT_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      loadPromise = null;
      reject(new Error("Could not load the Razorpay checkout script."));
    };
    document.body.appendChild(script);
  });
  return loadPromise;
}
