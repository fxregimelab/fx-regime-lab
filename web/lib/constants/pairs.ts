/**
 * Per-pair constants. `label` matches `signals.pair` and Python `regime_calls.pair` (EURUSD, …).
 * Legacy or manual rows may use slash display (`EUR/USD`) or lowercase; queries merge variants via
 * {@link regimeCallsPairFilterValues}.
 * `urlSlug` is the `[pair]` URL segment under `/terminal/[strategy]/…` (lowercase, no separators).
 */
export const PAIRS = [
  {
    label: 'EURUSD',
    display: 'EUR/USD',
    urlSlug: 'eurusd',
    terminalPath: '/terminal/fx-regime/eurusd',
    pairColor: '#4f6bed',
  },
  {
    label: 'USDJPY',
    display: 'USD/JPY',
    urlSlug: 'usdjpy',
    terminalPath: '/terminal/fx-regime/usdjpy',
    pairColor: '#e85d8e',
  },
  {
    label: 'USDINR',
    display: 'USD/INR',
    urlSlug: 'usdinr',
    terminalPath: '/terminal/fx-regime/usdinr',
    pairColor: '#2bb673',
  },
] as const;

export type PairLabel = (typeof PAIRS)[number]['label'];

/** Values to pass to PostgREST `pair.in.(...)` for `regime_calls` / `signals` (canonical + legacy). */
export function regimeCallsPairFilterValues(pair: string): string[] {
  const normalized = pair.replace(/[^a-z0-9]/gi, '').toLowerCase();
  const p = PAIRS.find(
    (x) =>
      x.label === pair ||
      x.label === pair.toUpperCase() ||
      x.display === pair ||
      x.urlSlug === normalized,
  );
  if (!p) {
    return Array.from(new Set([pair, pair.toUpperCase(), pair.toLowerCase(), normalized]));
  }
  return Array.from(
    new Set<string>([p.label, p.display, p.label.toLowerCase(), p.urlSlug]),
  );
}
