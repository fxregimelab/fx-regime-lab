import { PAIR_LABELS } from '@/lib/pair-styles';
import type { Database } from '@/lib/supabase/database.types';
import type {
  HeatmapData,
  HistoryRow,
  MacroEvent,
  RegimeCall,
  SignalRow,
  ValidationRow,
} from '@/lib/types';

type RegimeCallDb = Database['public']['Tables']['regime_calls']['Row'];
type SignalDb = Database['public']['Tables']['signals']['Row'];
type MacroDb = Database['public']['Tables']['macro_events']['Row'];
type ValidationDb = Database['public']['Tables']['validation_log']['Row'];

const RATE_SIGS = ['BULLISH', 'BEARISH', 'NEUTRAL'] as const;
type RateSig = (typeof RATE_SIGS)[number];

function asRateSignal(v: string | null | undefined): RateSig {
  const u = (v ?? 'NEUTRAL').toUpperCase();
  return RATE_SIGS.includes(u as RateSig) ? (u as RateSig) : 'NEUTRAL';
}

const MACRO_CATS = ['US', 'EU', 'JP', 'IN', 'UK'] as const;

export function mapHeatmapRows(
  rows: Array<{ date: string; pair: string; regime: string }>
): HeatmapData {
  const dateSet = new Set<string>();
  for (const r of rows) dateSet.add(r.date);
  const dates = Array.from(dateSet)
    .sort((a, b) => b.localeCompare(a))
    .slice(0, 30);
  const regimes: Record<string, string[]> = {};
  for (const pair of PAIR_LABELS) {
    const pr = rows.filter((r) => r.pair === pair);
    regimes[pair] = dates.map((d) => pr.find((r) => r.date === d)?.regime ?? 'UNKNOWN');
  }
  return { dates, regimes };
}

export function mapRegimeCallRow(row: RegimeCallDb): RegimeCall {
  return {
    pair: row.pair,
    date: row.date,
    regime: row.regime,
    confidence: row.confidence ?? 0,
    signal_composite: row.signal_composite ?? 0,
    rate_signal: asRateSignal(row.rate_signal),
    primary_driver: row.primary_driver ?? '',
    created_at: row.created_at ?? '',
  };
}

export function defaultSignalRow(pair: string, date: string): SignalRow {
  return {
    pair,
    date,
    rate_diff_2y: 0,
    cot_percentile: 0,
    realized_vol_20d: 0,
    realized_vol_5d: 0,
    implied_vol_30d: null,
    spot: 0,
    day_change: null,
    day_change_pct: null,
    created_at: '',
  };
}

export function mapSignalRow(row: SignalDb): SignalRow {
  return {
    pair: row.pair,
    date: row.date,
    rate_diff_2y: row.rate_diff_2y ?? 0,
    cot_percentile: row.cot_percentile ?? 0,
    realized_vol_20d: row.realized_vol_20d ?? 0,
    realized_vol_5d: row.realized_vol_5d ?? 0,
    implied_vol_30d: row.implied_vol_30d,
    spot: row.spot ?? 0,
    day_change: null,
    day_change_pct: null,
    created_at: row.created_at ?? '',
  };
}

type SignalDbRow = Parameters<typeof mapSignalRow>[0];

/** Map the latest signal row, computing day-over-day spot change from the previous row. */
export function mapSignalRowWithChange(rows: SignalDbRow[]): SignalRow {
  const row = rows[0];
  if (!row) return defaultSignalRow('', '');
  const prev = rows[1];
  const dayChange =
    prev?.spot != null && row?.spot != null ? row.spot - prev.spot : null;
  const dayChangePct =
    prev?.spot != null && row?.spot != null && prev.spot !== 0
      ? ((row.spot - prev.spot) / prev.spot) * 100
      : null;
  return { ...mapSignalRow(row), day_change: dayChange, day_change_pct: dayChangePct };
}

export function mapMacroEventRow(row: MacroDb): MacroEvent {
  const c = row.category ?? 'US';
  const category = MACRO_CATS.includes(c as (typeof MACRO_CATS)[number])
    ? (c as MacroEvent['category'])
    : 'US';
  const impact =
    row.impact === 'HIGH' || row.impact === 'MEDIUM' || row.impact === 'LOW' ? row.impact : 'LOW';
  return {
    date: row.date,
    event: row.event,
    impact,
    pairs: row.pairs ?? [],
    category,
    ai_brief: row.ai_brief,
  };
}

export function mapHistoryRow(row: {
  date: string;
  regime: string;
  confidence: number | null;
}): HistoryRow {
  return {
    date: row.date,
    regime: row.regime,
    confidence: row.confidence ?? 0,
  };
}

export function mapValidationRow(row: ValidationDb): ValidationRow | null {
  if (row.correct_1d == null || row.predicted_regime == null || row.actual_return_1d == null) {
    return null;
  }
  return {
    date: row.date,
    pair: row.pair,
    call: row.predicted_regime,
    outcome: row.correct_1d ? 'correct' : 'incorrect',
    return_pct: row.actual_return_1d,
  };
}

export function mapEquityCurve(
  rows: Array<{ date: string; pair: string; return_pct: number | null }>
): { dates: string[]; series: Record<string, number[]> } {
  const dateSet = new Set<string>();
  for (const r of rows) dateSet.add(r.date);
  const dates = Array.from(dateSet).sort();

  const running: Record<string, number> = {};
  const series: Record<string, number[]> = {};
  for (const p of PAIR_LABELS) {
    running[p] = 0;
    series[p] = [];
  }
  running.ALL = 0;
  series.ALL = [];

  for (const d of dates) {
    const dayRows = rows.filter((r) => r.date === d);
    let daySum = 0;
    let dayCount = 0;
    for (const p of PAIR_LABELS) {
      const hit = dayRows.find((r) => r.pair === p);
      const ret = hit?.return_pct ?? 0;
      running[p] = (running[p] ?? 0) + ret;
      const accP = series[p];
      if (accP) accP.push(running[p] ?? 0);
      daySum += ret;
      dayCount++;
    }
    running.ALL = (running.ALL ?? 0) + (dayCount > 0 ? daySum / dayCount : 0);
    const accAll = series.ALL;
    if (accAll) accAll.push(running.ALL ?? 0);
  }

  return { dates, series };
}
