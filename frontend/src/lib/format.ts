/**
 * INR is the backend's default currency (BusinessSettings.currency, see
 * backend/app/models/business.py). Per-business currency selection is a
 * Settings-phase feature; this formatter isn't hardcoding a business
 * choice, just matching the current backend default.
 */
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-IN").format(value);
}

/** Minutes elapsed since an ISO timestamp — used for KOT/order age, not a
 * localized string (callers combine it with an i18n unit label). */
export function minutesSince(isoTimestamp: string): number {
  const elapsedMs = Date.now() - new Date(isoTimestamp).getTime();
  return Math.max(0, Math.floor(elapsedMs / 60_000));
}
