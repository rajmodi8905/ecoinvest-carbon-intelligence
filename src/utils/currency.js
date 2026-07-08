/**
 * Currency formatting utilities for the Carbon Intelligence terminal.
 *
 * Indian NSE/BSE stocks (ticker suffix .NS or .BO) are priced in INR (₹).
 * All other tickers (US stocks) are priced in USD ($).
 */

/**
 * Returns the currency symbol for a given ticker.
 * @param {string} ticker - e.g. "TSLA", "SUZLON.NS", "ITC.BO"
 * @returns {string} "₹" for Indian stocks, "$" otherwise
 */
export const getCurrencySymbol = (ticker = '') => {
  const t = (ticker || '').toUpperCase();
  return t.endsWith('.NS') || t.endsWith('.BO') ? '₹' : '$';
};

/**
 * Format a price value with the correct currency symbol.
 * @param {number|string} value  - numeric price
 * @param {string}        ticker - stock ticker to infer currency
 * @param {number}        decimals - decimal places (default 2)
 * @returns {string} e.g. "$88.47" or "₹280.65"
 */
export const fmtTickerPrice = (value, ticker = '', decimals = 2) => {
  if (value == null || value === '') return '—';
  const num = parseFloat(value);
  if (isNaN(num)) return '—';
  const sym = getCurrencySymbol(ticker);
  return `${sym}${num.toFixed(decimals)}`;
};

/**
 * Convenience: plain USD price (for carbon credit prices — always USD).
 */
export const fmtUSDPrice = (value, decimals = 2) => {
  if (value == null || value === '') return '—';
  const num = parseFloat(value);
  if (isNaN(num)) return '—';
  return `$${num.toFixed(decimals)}`;
};
