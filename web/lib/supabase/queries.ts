import { PAIR_LABELS } from '@/lib/pair-styles';
import { mapEquityCurve } from '@/lib/supabase/map-row';
import { createClient } from './client';
import type { Database } from './database.types';

type RegimeCallRow = Database['public']['Tables']['regime_calls']['Row'];
type ValidationStatsRow = Pick<
  Database['public']['Tables']['validation_log']['Row'],
  'correct_1d' | 'actual_return_1d' | 'date'
>;

function utcDateString(d: Date): string {
  return d.toISOString().slice(0, 10);
}

/** Latest regime call per tracked pair (deduped in application code). */
export async function getLatestRegimeCalls() {
  const supabase = createClient();
  const res = await supabase
    .from('regime_calls')
    .select('*')
    .in('pair', PAIR_LABELS)
    .order('date', { ascending: false });

  if (res.error) {
    return res;
  }

  const raw = (res.data ?? []) as RegimeCallRow[];
  const seen = new Set<string>();
  const deduped: RegimeCallRow[] = [];
  for (const row of raw) {
    if (seen.has(row.pair)) continue;
    seen.add(row.pair);
    deduped.push(row);
    if (deduped.length === PAIR_LABELS.length) break;
  }

  return { data: deduped, error: null };
}

export async function getRegimeHeatmap() {
  const supabase = createClient();
  const start = new Date();
  start.setDate(start.getDate() - 30);
  return supabase
    .from('regime_calls')
    .select('date, pair, regime')
    .in('pair', PAIR_LABELS)
    .gte('date', utcDateString(start))
    .order('date', { ascending: false });
}

export async function getRegimeHistory(pair: string) {
  const supabase = createClient();
  return supabase
    .from('regime_calls')
    .select('date, regime, confidence')
    .eq('pair', pair)
    .order('date', { ascending: false })
    .limit(90);
}

export async function getLatestSignals(pair: string) {
  const supabase = createClient();
  return supabase
    .from('signals')
    .select('*')
    .eq('pair', pair)
    .order('date', { ascending: false })
    .limit(10);
}

export async function getLatestBrief(pair: string) {
  const supabase = createClient();
  return supabase
    .from('brief')
    .select('*')
    .eq('pair', pair)
    .order('date', { ascending: false })
    .limit(1);
}

export async function getUpcomingMacroEvents() {
  const supabase = createClient();
  const today = new Date();
  const end = new Date(today);
  end.setUTCDate(end.getUTCDate() + 14);
  const startStr = utcDateString(today);
  const endStr = utcDateString(end);

  return supabase
    .from('macro_events')
    .select('*')
    .gte('date', startStr)
    .lte('date', endStr)
    .in('impact', ['HIGH', 'MEDIUM'])
    .order('date', { ascending: true })
    .order('impact', { ascending: true });
}

export async function getValidationLog(limit = 30) {
  const supabase = createClient();
  return supabase.from('validation_log').select('*').order('date', { ascending: false }).limit(limit);
}

export async function getValidationStats() {
  const supabase = createClient();
  const res = await supabase
    .from('validation_log')
    .select('correct_1d, actual_return_1d, date')
    .order('date', { ascending: true });
  if (res.error) {
    return { data: null, error: res.error };
  }
  const rows = (res.data ?? []) as ValidationStatsRow[];
  if (!rows.length) {
    return { data: null, error: null };
  }
  const scored = rows.filter(
    (r): r is ValidationStatsRow & { correct_1d: boolean; actual_return_1d: number } =>
      r.correct_1d !== null && r.actual_return_1d !== null
  );
  const total = scored.length;
  const correct = scored.filter((r) => r.correct_1d === true).length;
  const winRate = total > 0 ? correct / total : 0;
  const sorted = [...scored].map((r) => r.actual_return_1d).sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  const medianReturn =
    sorted.length % 2 === 0
      ? ((sorted[mid - 1] ?? 0) + (sorted[mid] ?? 0)) / 2
      : (sorted[mid] ?? 0);
  const firstDate = rows[0]?.date;
  const daysLive = firstDate
    ? Math.ceil((Date.now() - new Date(firstDate).getTime()) / 86_400_000)
    : 0;
  return {
    data: { winRate, callsMade: total, medianReturn, daysLive },
    error: null,
  };
}

export async function getAllValidationRows() {
  const supabase = createClient();
  return supabase.from('validation_log').select('*').order('date', { ascending: false });
}

export async function getEquityCurve() {
  const supabase = createClient();
  return supabase
    .from('validation_log')
    .select('date, pair, actual_return_1d')
    .in('pair', PAIR_LABELS)
    .order('date', { ascending: true });
}

export type LastPipelineRunRow = Pick<RegimeCallRow, 'created_at'>;

export async function getLastPipelineRun() {
  const supabase = createClient();
  return supabase
    .from('regime_calls')
    .select('created_at')
    .order('created_at', { ascending: false })
    .limit(1)
    .returns<LastPipelineRunRow[]>();
}

type ValidationKpiRow = Pick<
  Database['public']['Tables']['validation_log']['Row'],
  'date' | 'correct_1d' | 'actual_return_1d' | 'pair'
>;

/** Homepage stats bar (shell design): pairs, calls since Apr 2026, rolling 7d accuracy, signal families. */
export async function getHomepageKpis() {
  const supabase = createClient();
  const res = await supabase
    .from('validation_log')
    .select('date, correct_1d, actual_return_1d')
    .order('date', { ascending: true });
  if (res.error) {
    return { data: null, error: res.error };
  }
  const rows = (res.data ?? []) as ValidationKpiRow[];
  const scored = rows.filter(
    (r): r is ValidationKpiRow & { correct_1d: boolean; actual_return_1d: number } =>
      r.correct_1d !== null && r.actual_return_1d !== null
  );
  const sinceApr = '2026-04-01';
  const callsSinceApril2026 = scored.filter((r) => r.date >= sinceApr).length;
  const cut = new Date();
  cut.setUTCDate(cut.getUTCDate() - 7);
  const cutStr = cut.toISOString().slice(0, 10);
  const last7 = scored.filter((r) => r.date >= cutStr);
  let accuracy7dPct: number | null = null;
  if (last7.length > 0) {
    const c = last7.filter((r) => r.correct_1d).length;
    accuracy7dPct = (c / last7.length) * 100;
  }
  return {
    data: {
      pairsTracked: PAIR_LABELS.length,
      callsSinceApril2026,
      accuracy7dPct,
      signalFamilies: 4,
    },
    error: null,
  };
}

/** Performance hero metrics aligned with shell prototype. */
export async function getShellPerformanceMetrics() {
  const supabase = createClient();
  const vRes = await supabase
    .from('validation_log')
    .select('date, correct_1d, actual_return_1d, pair')
    .order('date', { ascending: true });
  if (vRes.error) {
    return { data: null, error: vRes.error };
  }
  const rows = (vRes.data ?? []) as ValidationKpiRow[];
  const scored = rows.filter(
    (r): r is ValidationKpiRow & { correct_1d: boolean; actual_return_1d: number } =>
      r.correct_1d !== null && r.actual_return_1d !== null
  );
  const total = scored.length;
  const correct = scored.filter((r) => r.correct_1d).length;
  const cut7 = new Date();
  cut7.setUTCDate(cut7.getUTCDate() - 7);
  const cut7Str = cut7.toISOString().slice(0, 10);
  const slice7 = scored.filter((r) => r.date >= cut7Str);
  const rolling7dCorrect = slice7.filter((r) => r.correct_1d).length;
  const rolling7dTotal = slice7.length;
  const rolling7dPct =
    rolling7dTotal > 0 ? (rolling7dCorrect / rolling7dTotal) * 100 : null;
  const avgNextDayReturn =
    total > 0 ? scored.reduce((s, r) => s + r.actual_return_1d, 0) / total : null;
  const eRes = await getEquityCurve();
  let cumulativeAllLast: number | null = null;
  if (!eRes.error && eRes.data?.length) {
    const mapped = mapEquityCurve(
      (eRes.data as Array<{ date: string; pair: string; actual_return_1d: number | null }>).map((r) => ({
        date: r.date,
        pair: r.pair,
        return_pct: r.actual_return_1d,
      }))
    );
    const all = mapped.series.ALL ?? [];
    cumulativeAllLast = all.length ? all[all.length - 1] ?? null : null;
  }
  const perPairRolling: Record<string, { pct: number | null; n: number }> = {};
  for (const p of PAIR_LABELS) {
    const pr = scored.filter((r) => r.pair === p);
    const slice = pr.filter((r) => r.date >= cut7Str);
    const use = slice.length > 0 ? slice : pr;
    perPairRolling[p] = {
      pct: use.length ? (use.filter((r) => r.correct_1d).length / use.length) * 100 : null,
      n: use.length,
    };
  }
  return {
    data: {
      callsValidated: total,
      correct,
      rolling7dPct,
      rolling7dCorrect,
      rolling7dTotal,
      avgNextDayReturn,
      cumulativeAllLast,
      perPairRolling,
    },
    error: null,
  };
}

type RegimeTransitionRow = Pick<RegimeCallRow, 'date' | 'pair' | 'regime'>;

/** Ordered regime history for transition matrix (~2y window, ascending by date). */
export async function getRegimeCallsForTransitions() {
  const supabase = createClient();
  const start = new Date();
  start.setUTCDate(start.getUTCDate() - 730);
  return supabase
    .from('regime_calls')
    .select('date, pair, regime')
    .in('pair', PAIR_LABELS)
    .gte('date', utcDateString(start))
    .order('date', { ascending: true })
    .returns<RegimeTransitionRow[]>();
}
