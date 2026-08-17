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

/**
 * Same, but keeping paise. Whole-rupee rounding is fine for a dashboard
 * tile, and wrong anywhere the reader is checking that the numbers add up:
 * a 2.5% CGST and a 2.5% SGST of ₹6.50 each both render as "₹7" under the
 * rounding formatter, so the two lines appear to sum to ₹14 while the total
 * correctly says ₹13. Use this wherever individual lines are shown next to
 * the total they make up — tax previews, bills, receipts.
 */
export function formatCurrencyExact(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
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

/** Pure arithmetic only — no English text baked in here, since this is
 * used for a translated "updated Xs/Xm ago" label and every caller must
 * go through i18next's own pluralization (see dashboard.updatedJustNow /
 * updatedSecondsAgo / updatedMinutesAgo / updatedHoursAgo keys) rather
 * than a hardcoded "ago" string that Hindi/Marathi readers would see
 * untranslated in the middle of an otherwise-localized sentence. */
export function elapsedSince(sinceMs: number): { unit: "now" | "seconds" | "minutes" | "hours"; count: number } {
  const elapsedSeconds = Math.max(0, Math.floor((Date.now() - sinceMs) / 1000));
  if (elapsedSeconds < 5) return { unit: "now", count: 0 };
  if (elapsedSeconds < 60) return { unit: "seconds", count: elapsedSeconds };
  const minutes = Math.floor(elapsedSeconds / 60);
  if (minutes < 60) return { unit: "minutes", count: minutes };
  return { unit: "hours", count: Math.floor(minutes / 60) };
}
