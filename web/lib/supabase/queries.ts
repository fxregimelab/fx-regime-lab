import type { SupabaseClient } from '@supabase/supabase-js';
import { isRegimeLabel } from '@/lib/constants/regimes';
import { PAIRS, regimeCallsPairFilterValues } from '@/lib/constants/pairs';
import type { RegimeCall, RegimeLabel } from '@/lib/types/regime';
import type { SignalValue } from '@/lib/types/signal';
import type { ValidationRow } from '@/lib/types/validation';

const VALIDATION_DATE_PAGE = 1000;

export type ValidationHomeStrip = {
  totalRows: number;
  distinctDates: number;
  /** Most recent rows first; used for rolling-20 accuracy. */
  recentRows: ValidationRow[];
};

function rolling20AccuracyDisplay(rows: ValidationRow[]): string {
  const window = rows.slice(0, 20);
  const scored = window.filter((r) => r.correct_1d != null);
  if (scored.length < 5) return '—';
  const correct = scored.filter((r) => r.correct_1d === true).length;
  return `${Math.round((correct / scored.length) * 100)}%`;
}

export type BriefLogRow = {
  id: number;
  date: string;
  brief_text: string | null;
  eurusd_regime: string | null;
  usdjpy_regime: string | null;
  usdinr_regime: string | null;
  macro_context: string | null;
  created_at: string;
};

function parseRegimeCallRow(row: Record<string, unknown>): RegimeCall {
  const raw = typeof row.regime === 'string' ? row.regime : 'UNKNOWN';
  const regime: RegimeLabel = isRegimeLabel(raw) ? raw : 'UNKNOWN';
  return { ...(row as unknown as RegimeCall), regime };
}

/** Latest desk brief row from `brief_log`. */
export async function getLatestBrief(client: SupabaseClient) {
  return client.from('brief_log').select('*').order('date', { ascending: false }).limit(1).maybeSingle<BriefLogRow>();
}

/** Latest `regime_calls` row for one pair (canonical EURUSD-style label or URL slug). */
export async function getLatestRegimeCallForPair(client: SupabaseClient, pair: string) {
  const pairFilter = regimeCallsPairFilterValues(pair);
  const res = await client
    .from('regime_calls')
    .select('*')
    .in('pair', pairFilter)
    .order('date', { ascending: false })
    .limit(1);
  if (res.error) {
    return { data: null as RegimeCall | null, error: res.error };
  }
  const raw = res.data?.[0];
  if (!raw) {
    return { data: null as RegimeCall | null, error: null };
  }
  return { data: parseRegimeCallRow(raw as Record<string, unknown>), error: null };
}

/** Most recent `regime_calls` rows for one pair (e.g. 7-day history). */
export async function getRegimeHistoryForPair(
  client: SupabaseClient,
  pair: string,
  limit = 7,
) {
  const pairFilter = regimeCallsPairFilterValues(pair);
  const res = await client
    .from('regime_calls')
    .select('*')
    .in('pair', pairFilter)
    .order('date', { ascending: false })
    .limit(limit);
  if (res.error) {
    return { data: null as RegimeCall[] | null, error: res.error };
  }
  const rows = (res.data ?? []) as Record<string, unknown>[];
  return { data: rows.map((r) => parseRegimeCallRow(r)), error: null };
}

/** Latest regime call for each pair in [[PAIRS]] (parallel reads). Keys are merge labels (EURUSD, …). */
export async function getLatestRegimeCalls(client: SupabaseClient) {
  const labels = PAIRS.map((p) => p.label);
  const results = await Promise.all(labels.map((pair) => getLatestRegimeCallForPair(client, pair)));
  return { byPair: Object.fromEntries(labels.map((p, i) => [p, results[i].data])) as Record<
    (typeof labels)[number],
    RegimeCall | null
  >, errors: results.map((r) => r.error).filter(Boolean) };
}

/** Latest wide `signals` row for a pair (same pair key variants as `regime_calls`). */
export async function getSignalsForPair(client: SupabaseClient, pair: string) {
  const pairFilter = regimeCallsPairFilterValues(pair);
  const res = await client
    .from('signals')
    .select('*')
    .in('pair', pairFilter)
    .order('date', { ascending: false })
    .limit(1);
  if (res.error) {
    return { data: null as SignalValue | null, error: res.error };
  }
  const row = res.data?.[0];
  if (!row) {
    return { data: null as SignalValue | null, error: null };
  }
  return { data: row as SignalValue, error: null };
}

/** Recent `validation_log` rows, optionally filtered to one pair. */
export async function getValidationLog(
  client: SupabaseClient,
  options: { pair?: string; limit?: number } = {},
) {
  const limit = options.limit ?? 120;
  let q = client.from('validation_log').select('*').order('date', { ascending: false }).limit(limit);
  if (options.pair) {
    q = q.eq('pair', options.pair);
  }
  const { data, error } = await q;
  return { data: (data ?? []) as ValidationRow[], error };
}

/** Exact row count for `validation_log` (all pairs). */
export async function getValidationLogTotalCount(client: SupabaseClient) {
  const { count, error } = await client
    .from('validation_log')
    .select('*', { count: 'exact', head: true });
  if (error) {
    return { data: null as number | null, error };
  }
  return { data: count ?? 0, error: null };
}

/**
 * Distinct calendar `date` values in `validation_log` by paging `date` only.
 * Stops after empty page (full table scan; OK while table is modest).
 */
export async function getValidationDistinctDateCount(client: SupabaseClient) {
  const dates = new Set<string>();
  let from = 0;
  while (true) {
    const { data, error } = await client
      .from('validation_log')
      .select('date')
      .order('date', { ascending: true })
      .range(from, from + VALIDATION_DATE_PAGE - 1);
    if (error) {
      return { data: null as number | null, error };
    }
    if (!data?.length) break;
    for (const row of data) {
      if (typeof row.date === 'string') dates.add(row.date);
    }
    if (data.length < VALIDATION_DATE_PAGE) break;
    from += VALIDATION_DATE_PAGE;
  }
  return { data: dates.size, error: null };
}

/** Bundle for home track-record strip: counts + recent rows for rolling 20d accuracy. */
export async function getValidationHomeStrip(client: SupabaseClient) {
  const [countRes, distinctRes, recentRes] = await Promise.all([
    getValidationLogTotalCount(client),
    getValidationDistinctDateCount(client),
    getValidationLog(client, { limit: 80 }),
  ]);

  const firstError = countRes.error ?? distinctRes.error ?? recentRes.error;
  if (firstError) {
    return { data: null as ValidationHomeStrip | null, error: firstError };
  }
  if (countRes.data == null || distinctRes.data == null) {
    return { data: null as ValidationHomeStrip | null, error: null };
  }

  return {
    data: {
      totalRows: countRes.data,
      distinctDates: distinctRes.data,
      recentRows: recentRes.data,
    } satisfies ValidationHomeStrip,
    error: null,
  };
}

/** Rolling 20-row (date-desc) 1d accuracy label for strip; "—" if &lt; 5 scored rows in window. */
export function getValidationRolling20Display(recentRows: ValidationRow[]) {
  return rolling20AccuracyDisplay(recentRows);
}
