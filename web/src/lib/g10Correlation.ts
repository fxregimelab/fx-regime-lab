import type { Database } from "./supabase/database.types";

type HistoricalPricesRow =
  Database["public"]["Tables"]["historical_prices"]["Row"];

export type CorrelationMatrix = {
  pair: string;
  correlations: Record<string, number>;
}[];

export type CorrelationCell = {
  rowPair: string;
  colPair: string;
  value: number;
  label: string;
  color: string;
};

export function computeCorrelationMatrix(
  rows: HistoricalPricesRow[],
  pairs: string[],
): CorrelationMatrix {
  const byPair = new Map<string, HistoricalPricesRow[]>();
  for (const row of rows) {
    if (!pairs.includes(row.pair)) continue;
    const arr = byPair.get(row.pair) ?? [];
    arr.push(row);
    byPair.set(row.pair, arr);
  }

  const result: CorrelationMatrix = [];
  for (const p of pairs) {
    const correlations: Record<string, number> = {};
    for (const q of pairs) {
      if (p === q) {
        correlations[q] = 1;
        continue;
      }
      const pRows = byPair.get(p) ?? [];
      const qRows = byPair.get(q) ?? [];
      const pMap = new Map(pRows.map((r) => [r.date, r.close]));
      const qMap = new Map(qRows.map((r) => [r.date, r.close]));
      const commonDates = Array.from(pMap.keys()).filter((d) => qMap.has(d));
      const pVals = commonDates.map((d) => pMap.get(d)!);
      const qVals = commonDates.map((d) => qMap.get(d)!);
      if (pVals.length < 2) {
        correlations[q] = 0;
        continue;
      }
      const meanP = pVals.reduce((a, b) => a + b, 0) / pVals.length;
      const meanQ = qVals.reduce((a, b) => a + b, 0) / qVals.length;
      let num = 0;
      let denP = 0;
      let denQ = 0;
      for (let i = 0; i < pVals.length; i++) {
        const dp = pVals[i] - meanP;
        const dq = qVals[i] - meanQ;
        num += dp * dq;
        denP += dp * dp;
        denQ += dq * dq;
      }
      const denom = Math.sqrt(denP * denQ);
      correlations[q] = denom === 0 ? 0 : num / denom;
    }
    result.push({ pair: p, correlations });
  }
  return result;
}

export function correlationColor(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 0.8) return value > 0 ? "#059669" : "#dc2626"; // emerald-600 / red-600
  if (abs >= 0.6) return value > 0 ? "#10b981" : "#ef4444"; // emerald-500 / red-500
  if (abs >= 0.4) return value > 0 ? "#34d399" : "#f87171"; // emerald-400 / red-400
  if (abs >= 0.2) return value > 0 ? "#6ee7b7" : "#fca5a5"; // emerald-300 / red-300
  return "#d4d4d8"; // zinc-300
}

export function correlationLabel(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 0.8) return "Very Strong";
  if (abs >= 0.6) return "Strong";
  if (abs >= 0.4) return "Moderate";
  if (abs >= 0.2) return "Weak";
  return "None";
}

export function flattenMatrix(matrix: CorrelationMatrix): CorrelationCell[] {
  const cells: CorrelationCell[] = [];
  for (const row of matrix) {
    for (const [colPair, value] of Object.entries(row.correlations)) {
      cells.push({
        rowPair: row.pair,
        colPair,
        value,
        label: correlationLabel(value),
        color: correlationColor(value),
      });
    }
  }
  return cells;
}

export function getPairCorrelation(
  matrix: CorrelationMatrix,
  pairA: string,
  pairB: string,
): number {
  const row = matrix.find((r) => r.pair === pairA);
  if (!row) return 0;
  return row.correlations[pairB] ?? 0;
}

/* ─── Legacy exports (used by terminal/fx-regime page) ─── */

/** Canonical G10 FX order (matches `get_g10_correlation_matrix` in Postgres). */
export const G10_MATRIX_ORDER = ["EURUSD", "USDJPY", "USDINR"] as const;

/** Nested JSON from `get_g10_correlation_matrix`: only `pa < pb` keys populated. */
export type G10CorrelationJson = Record<string, Record<string, number>>;

export function parseG10CorrelationJson(raw: unknown): G10CorrelationJson {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return {};
  return raw as G10CorrelationJson;
}

export function correlationFromJson(
  m: G10CorrelationJson,
  a: string,
  b: string,
): number {
  if (a === b) return 1;
  if (a < b) {
    const v = m[a]?.[b];
    return typeof v === "number" && Number.isFinite(v) ? v : 0;
  }
  const v = m[b]?.[a];
  return typeof v === "number" && Number.isFinite(v) ? v : 0;
}

/** Strongest co-movement vs `pair` (max |ρ|), tie-break toward higher raw ρ. */
export function topCorrelatedPeer(
  matrix: G10CorrelationJson,
  pair: string,
  universe: readonly string[] = G10_MATRIX_ORDER,
): string | null {
  const peers = universe.filter((p) => p !== pair);
  if (peers.length === 0) return null;
  // biome-ignore lint/style/noNonNullAssertion: safe after length guard
  let bestP = peers[0]!;
  let bestC = correlationFromJson(matrix, pair, bestP);
  let bestAbs = Math.abs(bestC);
  for (let i = 1; i < peers.length; i++) {
    // biome-ignore lint/style/noNonNullAssertion: safe after length guard
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
