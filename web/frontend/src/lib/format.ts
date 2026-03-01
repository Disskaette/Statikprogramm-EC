/**
 * Formatting and parsing helpers for the Durchlaufträger frontend.
 *
 * German engineering convention: decimal comma instead of decimal point.
 * All helpers here bridge between user-facing strings and numeric values.
 */

/**
 * Parse a number string that may use German comma notation.
 *
 * Examples:
 *   "7,41"  → 7.41
 *   "7.41"  → 7.41
 *   "5"     → 5
 *   ""      → NaN
 */
export function parseGermanNumber(value: string): number {
  return parseFloat(value.replace(",", "."));
}

/**
 * Format a number for display using German locale (decimal comma).
 *
 * Examples:
 *   formatNumber(7.41)      → "7,41"
 *   formatNumber(5.0, 1)    → "5,0"
 *   formatNumber(300, 0)    → "300"
 */
export function formatNumber(value: number, decimals = 2): string {
  return value.toLocaleString("de-DE", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}
