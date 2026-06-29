export const PAIR_DISPLAY: Record<string, string> = {
  EURUSD: "EUR/USD",
  USDJPY: "USD/JPY",
  USDINR: "USD/INR",
  ALL: "ALL",
};

export const PAIR_CODE: Record<string, string> = {
  "EUR/USD": "EURUSD",
  "USD/JPY": "USDJPY",
  "USD/INR": "USDINR",
};

/** Map internal pair code (EURUSD) to display label (EUR/USD). */
export function formatPairCode(code: string): string {
  return PAIR_DISPLAY[code] ?? code;
}

/** Map display label (EUR/USD) to internal pair code (EURUSD). */
export function formatPairDisplay(display: string): string {
  return PAIR_CODE[display] ?? display;
}
