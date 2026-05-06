/** Canonical G10 FX order (matches `get_g10_correlation_matrix` in Postgres). */
export const G10_MATRIX_ORDER = [
  'EURUSD',
  'USDJPY',
  'USDINR',
] as const;

/** Nested JSON from `get_g10_correlation_matrix`: only `pa < pb` keys populated. */
export type G10CorrelationJson = Record<string, Record<string, number>>;

export function parseG10CorrelationJson(raw: unknown): G10CorrelationJson {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {};
  return raw as G10CorrelationJson;
}

export function correlationFromJson(m: G10CorrelationJson, a: string, b: string): number {
  if (a === b) return 1;
  if (a < b) {
    const v = m[a]?.[b];
    return typeof v === 'number' && Number.isFinite(v) ? v : 0;
  }
  const v = m[b]?.[a];
  return typeof v === 'number' && Number.isFinite(v) ? v : 0;
}

/** Strongest co-movement vs `pair` (max |ρ|), tie-break toward higher raw ρ. */
export function topCorrelatedPeer(
  matrix: G10CorrelationJson,
  pair: string,
  universe: readonly string[] = G10_MATRIX_ORDER,
): string | null {
  const peers = universe.filter((p) => p !== pair);
  if (peers.length === 0) return null;
  let bestP = peers[0]!;
  let bestC = correlationFromJson(matrix, pair, bestP);
  let bestAbs = Math.abs(bestC);
  for (let i = 1; i < peers.length; i++) {
    const p = peers[i]!;
    const c = correlationFromJson(matrix, pair, p);
    const abs = Math.abs(c);
    if (abs > bestAbs || (abs === bestAbs && c > bestC)) {
      bestP = p;
      bestC = c;
      bestAbs = abs;
    }
  }
  return bestP;
}
