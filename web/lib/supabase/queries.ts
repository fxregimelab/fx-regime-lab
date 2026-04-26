import { PAIR_LABELS } from '@/lib/pair-styles';
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

export async function getValidationLog() {
  const supabase = createClient();
  return supabase.from('validation_log').select('*').order('date', { ascending: false }).limit(30);
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
