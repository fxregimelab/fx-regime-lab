import { useMutation, useQuery } from '@tanstack/react-query';
import { supabase } from './supabase/client';
import type { Database } from './supabase/database.types';

type BriefLogRow = Database['public']['Tables']['brief_log']['Row'];
type BriefRow = Database['public']['Tables']['brief']['Row'];
type ValidationLogRow = Database['public']['Tables']['validation_log']['Row'];
type EquityRow = Pick<ValidationLogRow, 'date' | 'pair' | 'actual_return_1d'>;
type MacroEventRow = Database['public']['Tables']['macro_events']['Row'];
type EventRiskMatrixRow = Database['public']['Tables']['event_risk_matrices']['Row'];
type RegimeCallRow = Database['public']['Tables']['regime_calls']['Row'];
type SignalRow = Database['public']['Tables']['signals']['Row'];
type StrategyLedgerRow = Database['public']['Tables']['strategy_ledger']['Row'];
type DeskOpenCardRow = Database['public']['Tables']['desk_open_cards']['Row'];
type ResearchMemoRow = Database['public']['Tables']['research_memos']['Row'];
export type LatestRegimeCallRow = Pick<
  RegimeCallRow,
  'pair' | 'date' | 'regime' | 'confidence' | 'signal_composite'  | 'rate_signal'
  | 'cot_signal'
  | 'vol_signal'
  | 'rr_signal'
  | 'oi_signal'
  | 'primary_driver'
  | 'created_at'
>;
export type LatestSignalRow = Pick<
  SignalRow,
  | 'pair'
  | 'date'
  | 'spot'
  | 'rate_diff_2y'
  | 'rate_diff_10y'
  | 'cot_percentile'
  | 'realized_vol_20d'
  | 'realized_vol_5d'
  | 'implied_vol_30d'
  | 'cross_asset_vix'
  | 'cross_asset_dxy'
  | 'cross_asset_oil'
  | 'cross_asset_us10y'
  | 'cross_asset_gold'
  | 'cross_asset_copper'
  | 'cross_asset_stoxx'
  | 'day_change_pct'
  | 'cot_lev_money_net'
  | 'oi_delta'
  | 'created_at'
>;

export type { StrategyLedgerRow };

/** DB-backed FX universe (pair list). Prefer this over hardcoded arrays. */
export function useUniverse() {
  return useQuery({
    queryKey: ['universe', 'fx_pairs'],
    queryFn: async (): Promise<string[]> => {
      const { data, error } = await supabase
        .from('universe')
        .select('pair')
        .eq('class', 'FX')
        .order('pair', { ascending: true });
      if (error) throw error;
      return ((data ?? []) as { pair: string }[]).map((r) => r.pair);
    },
    staleTime: 60 * 60 * 1000,
  });
}

/** Forward-walking ledger rows for Alpha Ledger dashboard (non-neutral only). */
export function useStrategyLedger(pair: string) {
  type Row = Pick<
    StrategyLedgerRow,
    | 'id'
    | 'date'
    | 'pair'
    | 'regime'
    | 'primary_driver'
    | 'direction'
    | 'entry_close'
    | 'confidence'
    | 't1_close'
    | 't3_close'
    | 't5_close'
    | 't1_hit'
    | 't3_hit'
    | 't5_hit'
    | 'brier_score_t5'
  >;
  return useQuery({
    queryKey: ['strategy_ledger', pair],
    queryFn: async (): Promise<Row[]> => {
      const { data, error } = await supabase
        .from('strategy_ledger')
        .select(
          'id,date,pair,regime,primary_driver,direction,entry_close,confidence,t1_close,t3_close,t5_close,t1_hit,t3_hit,t5_hit,brier_score_t5',
        )
        .eq('pair', pair)
        .neq('direction', 'NEUTRAL')
        .order('date', { ascending: false })
        .limit(1000);
      if (error) throw error;
      return (data as Row[]) ?? [];
    },
    enabled: !!pair,
  });
}

export type DominanceItem = {
  rank: number;
  signal_family: string;
  signal_strength: number;
  beta: number;
  dominance_score: number;
};

export type MarkovPayload = {
  continuation_probability: number;
  transitions: Record<string, number>;
  weighted_sample_size?: number;
};

export type TelemetryAuditPayload = {
  cot_is_stale?: boolean;
  cot_age_days?: number | null;
  underwater_triggered?: boolean;
  parameter_instability?: boolean;
  weighted_sample_size?: number;
  overnight_day_change_pct?: number;
  Systemic_Cluster?: boolean;
  overnight_vol_threshold?: number;
  overnight_vix?: number | null;
  overnight_dxy?: number | null;
  overnight_vix_triggered?: boolean;
};

// getLatestRegimeCalls
export function useLatestRegimeCalls() {
  const universeQ = useUniverse();
  const pairs = universeQ.data ?? [];
  return useQuery({
    queryKey: ['regime_calls', 'latest', pairs],
    queryFn: async (): Promise<Record<string, LatestRegimeCallRow>> => {
      const { data, error } = await supabase
        .from('regime_calls')
        .select('pair,date,regime,confidence,signal_composite,rate_signal,cot_signal,vol_signal,rr_signal,oi_signal,primary_driver,created_at')
        .in('pair', pairs)
        .order('date', { ascending: false })
        .limit(20);

      if (error) throw error;

      // Deduplicate to get the latest per pair
      const latest: Record<string, LatestRegimeCallRow> = {};
      for (const row of (data as LatestRegimeCallRow[]) || []) {
        if (!latest[row.pair]) {
          latest[row.pair] = row;
        }
      }
      return latest;
    },
    enabled: universeQ.isSuccess && pairs.length > 0,
  });
}

// getRegimeHeatmap
export function useRegimeHeatmap() {
  const universeQ = useUniverse();
  const pairs = universeQ.data ?? [];
  return useQuery({
    queryKey: ['regime_calls', 'heatmap', pairs],
    queryFn: async (): Promise<{ date: string; pair: string; regime: string }[]> => {
      const d = new Date();
      d.setDate(d.getDate() - 30);
      const { data, error } = await supabase
        .from('regime_calls')
        .select('date, pair, regime')
        .in('pair', pairs)
        .gte('date', d.toISOString().split('T')[0])
        .order('date', { ascending: true });

      if (error) throw error;
      return (data as { date: string; pair: string; regime: string }[]) ?? [];
    },
    enabled: universeQ.isSuccess && pairs.length > 0,
  });
}

// getRegimeHistory30D — for chart regime bands
export function useRegimeHistory30D(pair: string) {
  return useQuery({
    queryKey: ['regime_calls', 'history30d', pair],
    queryFn: async (): Promise<{ date: string; regime: string; confidence: number }[]> => {
      const since = new Date();
      since.setDate(since.getDate() - 30);
      const { data, error } = await supabase
        .from('regime_calls')
        .select('date, regime, confidence')
        .eq('pair', pair)
        .gte('date', since.toISOString().split('T')[0])
        .order('date', { ascending: true });
      if (error) throw error;
      return (data as { date: string; regime: string; confidence: number }[]) ?? [];
    },
    enabled: !!pair,
  });
}

// getRegimeHistory
export function useRegimeHistory(pair: string) {
  return useQuery({
    queryKey: ['regime_calls', 'history', pair],
    queryFn: async (): Promise<{ date: string; regime: string; confidence: number }[]> => {
      const { data, error } = await supabase
        .from('regime_calls')
        .select('date, regime, confidence')
        .eq('pair', pair)
        .order('date', { ascending: false })
        .limit(90);
      if (error) throw error;
      return (data as { date: string; regime: string; confidence: number }[]) ?? [];
    },
    enabled: !!pair,
  });
}

// getLatestSignals
export function useLatestSignals() {
  const universeQ = useUniverse();
  const pairs = universeQ.data ?? [];
  return useQuery({
    queryKey: ['signals', 'latest', pairs],
    queryFn: async (): Promise<Record<string, LatestSignalRow>> => {
      const { data, error } = await supabase
        .from('signals')
        .select(
          'pair,date,spot,rate_diff_2y,rate_diff_10y,cot_percentile,realized_vol_20d,realized_vol_5d,implied_vol_30d,cross_asset_vix,cross_asset_dxy,cross_asset_oil,cross_asset_us10y,cross_asset_gold,cross_asset_copper,cross_asset_stoxx,day_change_pct,cot_lev_money_net,oi_delta,created_at',
        )
        .in('pair', pairs)
        .order('date', { ascending: false })
        .limit(20);

      if (error) throw error;
      const latest: Record<string, LatestSignalRow> = {};
      for (const row of (data as LatestSignalRow[]) || []) {
        if (!latest[row.pair]) {
          latest[row.pair] = row;
        }
      }
      return latest;
    },
    enabled: universeQ.isSuccess && pairs.length > 0,
  });
}

export function useCrossAssetPulse() {
  return useQuery({
    queryKey: ['signals', 'cross_asset_pulse'],
    queryFn: async (): Promise<{
      vix: { value: number | null; change: number | null };
      dxy: { value: number | null; change: number | null };
      oil: { value: number | null; change: number | null };
      us10y: { value: number | null; change: number | null };
      date: string | null;
    }> => {
      const { data, error } = await supabase
        .from('signals')
        .select('date,cross_asset_vix,cross_asset_dxy,cross_asset_oil,cross_asset_us10y')
        .eq('pair', 'EURUSD')
        .order('date', { ascending: false })
        .limit(2);
      if (error) throw error;
      const rows = (data ??
        []) as Pick<SignalRow, 'date' | 'cross_asset_vix' | 'cross_asset_dxy' | 'cross_asset_oil' | 'cross_asset_us10y'>[];
      const latest = rows[0];
      const prev = rows[1];
      const delta = (a: number | null, b: number | null) =>
        a != null && b != null ? a - b : null;
      return {
        vix: {
          value: latest?.cross_asset_vix ?? null,
          change: delta(latest?.cross_asset_vix ?? null, prev?.cross_asset_vix ?? null),
        },
        dxy: {
          value: latest?.cross_asset_dxy ?? null,
          change: delta(latest?.cross_asset_dxy ?? null, prev?.cross_asset_dxy ?? null),
        },
        oil: {
          value: latest?.cross_asset_oil ?? null,
          change: delta(latest?.cross_asset_oil ?? null, prev?.cross_asset_oil ?? null),
        },
        us10y: {
          value: latest?.cross_asset_us10y ?? null,
          change: delta(latest?.cross_asset_us10y ?? null, prev?.cross_asset_us10y ?? null),
        },
        date: latest?.date ?? null,
      };
    },
  });
}

// getLatestBrief
export function useLatestBrief() {
  return useQuery({
    queryKey: ['brief_log', 'latest'],
    queryFn: async (): Promise<BriefLogRow | null> => {
      const { data, error } = await supabase
        .from('brief_log')
        .select('*')
        .order('date', { ascending: false })
        .limit(1)
        .maybeSingle();
      if (error) throw error;
      return data as BriefLogRow | null;
    },
  });
}

// getUpcomingMacroEvents
export function useUpcomingMacroEvents() {
  return useQuery({
    queryKey: ['macro_events', 'upcoming'],
    queryFn: async (): Promise<MacroEventRow[]> => {
      const today = new Date().toISOString().split('T')[0];
      const future = new Date();
      future.setDate(future.getDate() + 14);
      const { data, error } = await supabase
        .from('macro_events')
        .select('*')
        .gte('date', today)
        .lte('date', future.toISOString().split('T')[0])
        .in('impact', ['HIGH', 'MEDIUM'])
        .order('date', { ascending: true });
      if (error) throw error;
      return (data as MacroEventRow[]) ?? [];
    },
  });
}

export function useEventRiskMatrices(pair: string) {
  return useQuery({
    queryKey: ['event_risk_matrices', pair, 'next_14d'],
    queryFn: async (): Promise<EventRiskMatrixRow[]> => {
      const today = new Date().toISOString().split('T')[0];
      const future = new Date();
      future.setDate(future.getDate() + 14);
      const { data, error } = await supabase
        .from('event_risk_matrices')
        .select('*')
        .eq('pair', pair)
        .gte('date', today)
        .lte('date', future.toISOString().split('T')[0])
        .order('date', { ascending: true });
      if (error) throw error;
      return (data as EventRiskMatrixRow[]) ?? [];
    },
    enabled: !!pair,
    staleTime: Infinity,
  });
}

// getValidationLog
export function useValidationLog(limit = 30) {
  return useQuery({
    queryKey: ['validation_log', limit],
    queryFn: async (): Promise<ValidationLogRow[]> => {
      const { data, error } = await supabase
        .from('validation_log')
        .select('*')
        .order('date', { ascending: false })
        .limit(limit);
      if (error) throw error;
      return (data as ValidationLogRow[]) ?? [];
    },
  });
}

// getEquityCurve
export function useEquityCurve() {
  const universeQ = useUniverse();
  const pairs = universeQ.data ?? [];
  return useQuery({
    queryKey: ['validation_log', 'equity', pairs],
    queryFn: async (): Promise<EquityRow[]> => {
      const { data, error } = await supabase
        .from('validation_log')
        .select('date, pair, actual_return_1d')
        .in('pair', pairs)
        .order('date', { ascending: true });
      if (error) throw error;
      return (data as EquityRow[]) ?? [];
    },
    enabled: universeQ.isSuccess && pairs.length > 0,
  });
}

// getLastPipelineRun
export function useLastPipelineRun() {
  return useQuery({
    queryKey: ['regime_calls', 'last_run'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('regime_calls')
        .select('created_at')
        .order('created_at', { ascending: false })
        .limit(1)
        .maybeSingle();
      if (error) throw error;
      return (data as { created_at?: string } | null)?.created_at ?? null;
    },
  });
}

/** Pivot flat regime_calls heatmap rows into per-pair regime arrays aligned to sorted dates. */
export function pivotRegimeHeatmapRows(
  rows: { date: string; pair: string; regime: string }[] | null | undefined,
  pairLabels: readonly string[],
) {
  if (!rows?.length) return { dates: [] as string[], regimes: {} as Record<string, string[]> };
  const dates = [...new Set(rows.map((r) => r.date))].sort();
  const regimes: Record<string, string[]> = {};
  for (const pl of pairLabels) {
    regimes[pl] = dates.map((d) => {
      const row = rows.find((r) => r.pair === pl && r.date === d);
      return row?.regime ?? 'NEUTRAL';
    });
  }
  return { dates, regimes };
}

/** Latest AI desk brief for a pair (OpenRouter output persisted by pipeline). */
export function usePairBrief(pair: string) {
  return useQuery({
    queryKey: ['brief', 'pair', pair],
    queryFn: async (): Promise<
      Pick<BriefRow, 'analysis' | 'date' | 'regime' | 'confidence' | 'composite' | 'primary_driver'> | null
    > => {
      const { data, error } = await supabase
        .from('brief')
        .select('analysis, date, regime, confidence, composite, primary_driver')
        .eq('pair', pair)
        .order('date', { ascending: false })
        .limit(1)
        .maybeSingle();
      if (error) throw error;
      return data as Pick<BriefRow, 'analysis' | 'date' | 'regime' | 'confidence' | 'composite' | 'primary_driver'> | null;
    },
    enabled: !!pair,
  });
}

export function useDeskOpenCard(pair: string) {
  return useQuery({
    queryKey: ['desk_open_cards', 'latest', pair],
    queryFn: async (): Promise<{
      date: string;
      pair: string;
      structural_regime: string;
      dominance_array: DominanceItem[];
      pain_index: number | null;
      markov_probabilities: MarkovPayload | null;
      ai_brief: string | null;
      telemetry_audit: TelemetryAuditPayload | null;
      parameter_instability: boolean;
      invalidation_triggered: boolean;
      telemetry_status: string;
      global_rank: number | null;
      apex_score: number | null;
      regime_age: number | null;
    } | null> => {
      const { data, error } = await supabase
        .from('desk_open_cards')
        .select('*')
        .eq('pair', pair)
        .order('date', { ascending: false })
        .limit(1)
        .maybeSingle();
      if (error) throw error;
      const row = data as DeskOpenCardRow | null;
      if (!row) return null;
      const audit = (row.telemetry_audit as TelemetryAuditPayload | null) ?? null;
      return {
        date: row.date,
        pair: row.pair,
        structural_regime: row.structural_regime,
        dominance_array: (row.dominance_array as DominanceItem[] | null) ?? [],
        pain_index: row.pain_index,
        markov_probabilities: (row.markov_probabilities as MarkovPayload | null) ?? null,
        ai_brief: row.ai_brief,
        telemetry_audit: audit,
        parameter_instability: Boolean(audit?.parameter_instability),
        invalidation_triggered: Boolean(row.invalidation_triggered),
        telemetry_status: row.telemetry_status ?? 'ONLINE',
        global_rank: row.global_rank ?? null,
        apex_score: row.apex_score ?? null,
        regime_age: row.regime_age ?? null,
      };
    },
    enabled: !!pair,
    staleTime: Infinity,
  });
}

/** Normalized desk row for homepage Apex / universe views. */
export type DeskOpenCardSnapshotRow = {
  date: string;
  pair: string;
  structural_regime: string;
  dominance_array: DominanceItem[];
  pain_index: number | null;
  markov_probabilities: MarkovPayload | null;
  ai_brief: string | null;
  telemetry_audit: TelemetryAuditPayload | null;
  /** From ``telemetry_audit.parameter_instability`` (beta / dominance disagreement). */
  parameter_instability: boolean;
  invalidation_triggered: boolean;
  telemetry_status: string;
  global_rank: number | null;
  apex_score: number | null;
  regime_age: number | null;
};

function mapDeskRow(row: DeskOpenCardRow): DeskOpenCardSnapshotRow {
  const audit = (row.telemetry_audit as TelemetryAuditPayload | null) ?? null;
  return {
    date: row.date,
    pair: row.pair,
    structural_regime: row.structural_regime,
    dominance_array: (row.dominance_array as DominanceItem[] | null) ?? [],
    pain_index: row.pain_index,
    markov_probabilities: (row.markov_probabilities as MarkovPayload | null) ?? null,
    ai_brief: row.ai_brief,
    telemetry_audit: audit,
    parameter_instability: Boolean(audit?.parameter_instability),
    invalidation_triggered: Boolean(row.invalidation_triggered),
    telemetry_status: row.telemetry_status ?? 'ONLINE',
    global_rank: row.global_rank ?? null,
    apex_score: row.apex_score ?? null,
    regime_age: row.regime_age ?? null,
  };
}

function utcPrevCalendarDay(isoDate: string): string {
  const d = new Date(`${isoDate}T12:00:00.000Z`);
  d.setUTCDate(d.getUTCDate() - 1);
  return d.toISOString().slice(0, 10);
}

/** Latest desk_open_cards snapshot: all tracked pairs for max(date), plus rank jumps vs prior calendar day. */
export function useLatestDeskOpenCardsSnapshot() {
  const universeQ = useUniverse();
  const pairs = universeQ.data ?? [];
  return useQuery({
    queryKey: ['desk_open_cards', 'snapshot', pairs],
    queryFn: async (): Promise<{
      asOfDate: string | null;
      cards: DeskOpenCardSnapshotRow[];
      rankJumpByPair: Record<string, number>;
    }> => {
      const { data: head, error: headErr } = await supabase
        .from('desk_open_cards')
        .select('date')
        .in('pair', pairs)
        .order('date', { ascending: false })
        .limit(1);
      if (headErr) throw headErr;
      const headRow = (head ?? [])[0] as { date: string } | undefined;
      const latest = headRow?.date ?? null;
      if (!latest) {
        return { asOfDate: null, cards: [], rankJumpByPair: {} };
      }

      const { data: rows, error } = await supabase
        .from('desk_open_cards')
        .select('*')
        .eq('date', latest)
        .in('pair', pairs);
      if (error) throw error;
      const cards = ((rows as DeskOpenCardRow[]) ?? []).map(mapDeskRow);

      const prevDay = utcPrevCalendarDay(latest);
      const { data: prevRows, error: prevErr } = await supabase
        .from('desk_open_cards')
        .select('pair, global_rank')
        .eq('date', prevDay)
        .in('pair', pairs);
      if (prevErr) throw prevErr;

      const prevRankByPair: Record<string, number> = {};
      for (const r of (prevRows as { pair: string; global_rank: number | null }[]) ?? []) {
        if (r.global_rank != null) prevRankByPair[r.pair] = r.global_rank;
      }

      const rankJumpByPair: Record<string, number> = {};
      for (const c of cards) {
        const prev = prevRankByPair[c.pair];
        const curr = c.global_rank;
        if (prev != null && curr != null && prev > curr) {
          rankJumpByPair[c.pair] = prev - curr;
        }
      }

      return { asOfDate: latest, cards, rankJumpByPair };
    },
    enabled: universeQ.isSuccess && pairs.length > 0,
    staleTime: 60000,
  });
}

export function useTelemetryStatus(pair: string) {
  return useQuery({
    queryKey: ['desk_open_cards', 'telemetry', pair],
    queryFn: async (): Promise<{ invalidation_triggered: boolean; telemetry_status: string } | null> => {
      const { data, error } = await supabase
        .from('desk_open_cards')
        .select('invalidation_triggered, telemetry_status')
        .eq('pair', pair)
        .order('date', { ascending: false })
        .limit(1)
        .maybeSingle();
      if (error) throw error;
      const row = data as Pick<DeskOpenCardRow, 'invalidation_triggered' | 'telemetry_status'> | null;
      if (!row) return null;
      return {
        invalidation_triggered: Boolean(row.invalidation_triggered),
        telemetry_status: row.telemetry_status ?? 'ONLINE',
      };
    },
    enabled: !!pair,
    staleTime: 60000,
    refetchInterval: 60000,
  });
}

/** Recent signal rows (oldest → newest) for sparklines. */
export function useSignalHistory(pair: string, limit = 14) {
  return useQuery({
    queryKey: ['signals', 'history', pair, limit],
    queryFn: async (): Promise<SignalRow[]> => {
      const { data, error } = await supabase
        .from('signals')
        .select('*')
        .eq('pair', pair)
        .order('date', { ascending: false })
        .limit(limit);
      if (error) throw error;
      return ((data as SignalRow[]) ?? []).slice().reverse();
    },
    enabled: !!pair,
  });
}

/** Deep historical OHLCV for MAX chart: daily inside 2Y, Friday-only snapshots older (server-side RPC). */
export function useHistoricalData(pair: string, enabled = false) {
  return useQuery({
    queryKey: ['signals', 'historical', 'max_thin', pair],
    queryFn: async (): Promise<
      Array<{ date: string; pair: string; open: number | null; high: number | null; low: number | null; close: number | null; volume: number | null }>
    > => {
      const cutoff = new Date();
      cutoff.setUTCFullYear(cutoff.getUTCFullYear() - 2);
      const cutoffStr = cutoff.toISOString().slice(0, 10);
      const { data, error } = await supabase.rpc(
        'historical_prices_for_max_chart',
        { p_pair: pair, p_cutoff: cutoffStr } as never,
      );
      if (error) throw error;
      return (
        (data as Array<{ date: string; pair: string; open: number | null; high: number | null; low: number | null; close: number | null; volume: number | null }>) ??
        []
      );
    },
    enabled: enabled && !!pair,
  });
}

export function useLatestResearchAnalogs(pair: string) {
  return useQuery({
    queryKey: ['research_analogs', 'latest', pair],
    queryFn: async (): Promise<
      Array<{
        as_of_date: string;
        pair: string;
        rank: number;
        match_date: string;
        match_score: number;
        forward_30d_return: number | null;
        regime_stability: number | null;
        context_label: string | null;
      }>
    > => {
      const { data, error } = await supabase
        .from('research_analogs')
        .select('as_of_date,pair,rank,match_date,match_score,forward_30d_return,regime_stability,context_label')
        .eq('pair', pair)
        .order('as_of_date', { ascending: false })
        .order('rank', { ascending: true })
        .limit(3);
      if (error) throw error;
      return (
        (data as Array<{
          as_of_date: string;
          pair: string;
          rank: number;
          match_date: string;
          match_score: number;
          forward_30d_return: number | null;
          regime_stability: number | null;
          context_label: string | null;
        }>) ?? []
      );
    },
    enabled: !!pair,
  });
}

/** Take last `targetLen` values; left-pad with first sample if short. */
export function sparkNumericSeries(values: number[], targetLen = 7): number[] {
  if (values.length === 0) return Array.from({ length: targetLen }, () => 0);
  let s = values.slice(-targetLen);
  const first = s[0] ?? 0;
  while (s.length < targetLen) {
    s = [first, ...s];
  }
  return s;
}

/** Forward-walking ledger: combined T+1 and T+3 hit rate (all pairs), excluding NEUTRAL rows. */
export async function getGlobalHitRate(days = 90): Promise<{
  hitRatePct: number | null;
  trials: number;
}> {
  const since = new Date();
  since.setUTCDate(since.getUTCDate() - days);
  const sinceStr = since.toISOString().slice(0, 10);

  let from = 0;
  const pageSize = 1000;
  let hits = 0;
  let trials = 0;

  for (;;) {
    const { data, error } = await supabase
      .from('strategy_ledger')
      .select('t1_hit,t3_hit')
      .gte('date', sinceStr)
      .neq('direction', 'NEUTRAL')
      .range(from, from + pageSize - 1);
    if (error) throw error;
    const rows = (data ?? []) as Pick<StrategyLedgerRow, 't1_hit' | 't3_hit'>[];
    for (const row of rows) {
      if (row.t1_hit != null) {
        trials += 1;
        hits += row.t1_hit === 1 ? 1 : 0;
      }
      if (row.t3_hit != null) {
        trials += 1;
        hits += row.t3_hit === 1 ? 1 : 0;
      }
    }
    if (rows.length < pageSize) break;
    from += pageSize;
  }

  const hitRatePct = trials > 0 ? (hits / trials) * 100 : null;
  return { hitRatePct, trials };
}

/** Client-side trust anchor for terminal rail (same logic as ``getGlobalHitRate(90)``). */
export function useVerified90dEdge() {
  return useQuery({
    queryKey: ['strategy_ledger', 'global_hit_rate', 90],
    queryFn: () => getGlobalHitRate(90),
    staleTime: 60 * 60 * 1000,
  });
}

export type GatewayLandingPayload = {
  verifiedEdgePct: number | null;
  pairs: string[];
  desk: {
    asOfDate: string | null;
    cards: DeskOpenCardSnapshotRow[];
    rankJumpByPair: Record<string, number>;
  };
  systemic: {
    dollarDominance: number | null;
    outlier: string | null;
  };
  signals: Record<string, LatestSignalRow>;
  regime: Record<string, LatestRegimeCallRow>;
};

async function fetchUniverseFxPairsServer(): Promise<string[]> {
  const { data, error } = await supabase
    .from('universe')
    .select('pair')
    .eq('class', 'FX')
    .order('pair', { ascending: true });
  if (error) throw error;
  return ((data ?? []) as { pair: string }[]).map((r) => r.pair);
}

async function fetchLatestBriefSystemicServer(): Promise<{
  dollarDominance: number | null;
  outlier: string | null;
}> {
  const { data, error } = await supabase
    .from('brief_log')
    .select('dollar_dominance,idiosyncratic_outlier')
    .order('date', { ascending: false })
    .limit(1)
    .maybeSingle();
  if (error) throw error;
  const row = data as { dollar_dominance: number | null; idiosyncratic_outlier: string | null } | null;
  return {
    dollarDominance: row?.dollar_dominance ?? null,
    outlier: row?.idiosyncratic_outlier ?? null,
  };
}

async function fetchLatestSignalsMapServer(pairs: string[]): Promise<Record<string, LatestSignalRow>> {
  if (pairs.length === 0) return {};
  const { data, error } = await supabase
    .from('signals')
    .select(
      'pair,date,spot,rate_diff_2y,rate_diff_10y,cot_percentile,realized_vol_20d,realized_vol_5d,implied_vol_30d,cross_asset_vix,cross_asset_dxy,cross_asset_oil,cross_asset_us10y,cross_asset_gold,cross_asset_copper,cross_asset_stoxx,day_change_pct,cot_lev_money_net,oi_delta,created_at',
    )
    .in('pair', pairs)
    .order('date', { ascending: false })
    .limit(20);
  if (error) throw error;
  const latest: Record<string, LatestSignalRow> = {};
  for (const row of (data as LatestSignalRow[]) || []) {
    if (!latest[row.pair]) {
      latest[row.pair] = row;
    }
  }
  return latest;
}

async function fetchLatestRegimeCallsMapServer(pairs: string[]): Promise<Record<string, LatestRegimeCallRow>> {
  if (pairs.length === 0) return {};
  const { data, error } = await supabase
    .from('regime_calls')
    .select(
      'pair,date,regime,confidence,signal_composite,rate_signal,cot_signal,vol_signal,rr_signal,oi_signal,primary_driver,created_at',
    )
    .in('pair', pairs)
    .order('date', { ascending: false })
    .limit(20);
  if (error) throw error;
  const latest: Record<string, LatestRegimeCallRow> = {};
  for (const row of (data as LatestRegimeCallRow[]) || []) {
    if (!latest[row.pair]) {
      latest[row.pair] = row;
    }
  }
  return latest;
}

async function fetchDeskOpenCardsSnapshotServer(pairs: string[]): Promise<{
  asOfDate: string | null;
  cards: DeskOpenCardSnapshotRow[];
  rankJumpByPair: Record<string, number>;
}> {
  if (pairs.length === 0) {
    return { asOfDate: null, cards: [], rankJumpByPair: {} };
  }
  const { data: head, error: headErr } = await supabase
    .from('desk_open_cards')
    .select('date')
    .in('pair', pairs)
    .order('date', { ascending: false })
    .limit(1);
  if (headErr) throw headErr;
  const headRow = (head ?? [])[0] as { date: string } | undefined;
  const latest = headRow?.date ?? null;
  if (!latest) {
    return { asOfDate: null, cards: [], rankJumpByPair: {} };
  }

  const { data: rows, error } = await supabase
    .from('desk_open_cards')
    .select('*')
    .eq('date', latest)
    .in('pair', pairs);
  if (error) throw error;
  const cards = ((rows as DeskOpenCardRow[]) ?? []).map(mapDeskRow);

  const prevDay = utcPrevCalendarDay(latest);
  const { data: prevRows, error: prevErr } = await supabase
    .from('desk_open_cards')
    .select('pair, global_rank')
    .eq('date', prevDay)
    .in('pair', pairs);
  if (prevErr) throw prevErr;

  const prevRankByPair: Record<string, number> = {};
  for (const r of (prevRows as { pair: string; global_rank: number | null }[]) ?? []) {
    if (r.global_rank != null) prevRankByPair[r.pair] = r.global_rank;
  }

  const rankJumpByPair: Record<string, number> = {};
  for (const c of cards) {
    const prev = prevRankByPair[c.pair];
    const curr = c.global_rank;
    if (prev != null && curr != null && prev > curr) {
      rankJumpByPair[c.pair] = prev - curr;
    }
  }

  return { asOfDate: latest, cards, rankJumpByPair };
}

export type ResearchMemoListItem = Pick<
  ResearchMemoRow,
  'id' | 'date' | 'title' | 'link_url' | 'ai_thesis_summary'
>;

/** Terminal: memo list + thesis JSON for archive HUD (sorted by date desc). */
export function useResearchMemosList() {
  return useQuery({
    queryKey: ['research_memos', 'list'],
    queryFn: async (): Promise<ResearchMemoListItem[]> => {
      const { data, error } = await supabase
        .from('research_memos')
        .select('id, date, title, link_url, ai_thesis_summary')
        .order('date', { ascending: false });
      if (error) throw error;
      return (data ?? []) as ResearchMemoListItem[];
    },
    staleTime: 5 * 60 * 1000,
  });
}

/** POST validated webhook URL; server encrypts and persists (Supabase service role). */
export function useConnectDeskWebhook() {
  return useMutation({
    mutationFn: async (payload: { webhookUrl: string; pairFilter?: string | null }) => {
      const res = await fetch('/api/connect-desk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = (await res.json().catch(() => ({}))) as { error?: string };
      if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
      return data;
    },
  });
}

/** Full memo body for reader overlay (not used in daily pipeline). */
export function useResearchMemoReader(id: string | null) {
  return useQuery({
    queryKey: ['research_memos', 'reader', id],
    queryFn: async (): Promise<
      Pick<ResearchMemoRow, 'id' | 'date' | 'title' | 'raw_content' | 'link_url'> | null
    > => {
      const { data, error } = await supabase
        .from('research_memos')
        .select('id, date, title, raw_content, link_url')
        .eq('id', id!)
        .maybeSingle();
      if (error) throw error;
      return data as Pick<
        ResearchMemoRow,
        'id' | 'date' | 'title' | 'raw_content' | 'link_url'
      > | null;
    },
    enabled: id != null && id.length > 0,
  });
}

/** SSR / SSG bundle for the gateway hero and desk telemetry (instant first paint). */
export async function getGatewayLandingData(): Promise<GatewayLandingPayload> {
  const pairs = await fetchUniverseFxPairsServer();
  const [edge, desk, systemic, signals, regime] = await Promise.all([
    getGlobalHitRate(90),
    fetchDeskOpenCardsSnapshotServer(pairs),
    fetchLatestBriefSystemicServer(),
    fetchLatestSignalsMapServer(pairs),
    fetchLatestRegimeCallsMapServer(pairs),
  ]);

  return {
    verifiedEdgePct: edge.hitRatePct,
    pairs,
    desk,
    systemic,
    signals,
    regime,
  };
}
