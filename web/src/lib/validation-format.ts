import type { Database } from '@/lib/supabase/database.types';

export type ValidationTableRow = {
  date: string;
  pair: string;
  call: string;
  outcome: string;
  return_pct: number;
};

type VRow = Database['public']['Tables']['validation_log']['Row'];

const PAIR_DISPLAY: Record<string, string> = {
  EURUSD: 'EUR/USD',
  USDJPY: 'USD/JPY',
  USDINR: 'USD/INR',
  GBPUSD: 'GBP/USD',
  AUDUSD: 'AUD/USD',
  USDCAD: 'USD/CAD',
  USDCHF: 'USD/CHF',
};

export function mapValidationLogToTableRows(
  rows: VRow[] | null | undefined,
  max = 200,
): ValidationTableRow[] {
  if (!rows?.length) return [];
  return rows
    .filter((r) => r.correct_1d !== null && r.actual_return_1d != null)
    .slice(0, max)
    .map((r) => ({
      date: r.date,
      pair: PAIR_DISPLAY[r.pair] ?? r.pair,
      call: r.predicted_regime ?? '—',
      outcome: r.correct_1d ? 'correct' : 'incorrect',
      return_pct: Number(r.actual_return_1d),
    }));
}

export function rolling7dAccuracyPct(rows: VRow[] | null | undefined): number | null {
  if (!rows?.length) return null;
  const scored = rows.filter((r) => r.correct_1d !== null && r.date);
  if (!scored.length) return null;
  const cut = new Date();
  cut.setUTCDate(cut.getUTCDate() - 7);
  const cutStr = cut.toISOString().slice(0, 10);
  const slice = scored.filter((r) => r.date >= cutStr);
  if (!slice.length) return null;
  const ok = slice.filter((r) => r.correct_1d).length;
  return (ok / slice.length) * 100;
}

export function callsValidatedSince(rows: VRow[] | null | undefined, sinceIsoDate: string): number {
  if (!rows?.length) return 0;
  return rows.filter((r) => r.date >= sinceIsoDate && r.correct_1d !== null).length;
}

export type EquityPoint = { date: string; cum: number };

/** Daily mean of `actual_return_1d` across tracked pairs, then cumulative sum. */
export function buildEquitySeries(
  rows: { date: string; pair: string; actual_return_1d: number | null }[] | null | undefined,
): { ALL: EquityPoint[]; byPair: Record<string, EquityPoint[]> } {
  if (!rows?.length) return { ALL: [], byPair: {} };
  const byDate = new Map<string, number[]>();
  const byPairDate = new Map<string, Map<string, number>>();
  for (const r of rows) {
    if (r.actual_return_1d == null) continue;
    const v = Number(r.actual_return_1d);
    const arr = byDate.get(r.date) ?? [];
    arr.push(v);
    byDate.set(r.date, arr);
    if (!byPairDate.has(r.pair)) byPairDate.set(r.pair, new Map());
    byPairDate.get(r.pair)!.set(r.date, v);
  }
  const dates = [...byDate.keys()].sort();
  let cum = 0;
  const ALL: EquityPoint[] = dates.map((d) => {
    const xs = byDate.get(d)!;
    cum += xs.reduce((a, b) => a + b, 0) / xs.length;
    return { date: d, cum };
  });
  const pairs = [...new Set(rows.map((r) => r.pair))];
  const byPair: Record<string, EquityPoint[]> = {};
  for (const p of pairs) {
    let c = 0;
    const m = byPairDate.get(p);
    byPair[p] = dates.map((d) => {
      const x = m?.get(d);
      if (x != null) c += x;
      return { date: d, cum: c };
    });
  }
  return { ALL, byPair };
}
