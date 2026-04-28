import { useQuery } from '@tanstack/react-query';
import { supabase } from './supabase/client';
import type { Database } from './supabase/database.types';

type BriefLogRow = Database['public']['Tables']['brief_log']['Row'];
type BriefRow = Database['public']['Tables']['brief']['Row'];
type ValidationLogRow = Database['public']['Tables']['validation_log']['Row'];
type EquityRow = Pick<ValidationLogRow, 'date' | 'pair' | 'actual_return_1d'>;
type MacroEventRow = Database['public']['Tables']['macro_events']['Row'];
type RegimeCallRow = Database['public']['Tables']['regime_calls']['Row'];
type SignalRow = Database['public']['Tables']['signals']['Row'];
type LatestRegimeCallRow = Pick<
  RegimeCallRow,
  'pair' | 'date' | 'regime' | 'confidence' | 'signal_composite'  | 'rate_signal'
  | 'cot_signal'
  | 'vol_signal'
  | 'rr_signal'
  | 'oi_signal'
  | 'primary_driver'
  | 'created_at'
>;
type LatestSignalRow = Pick<
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
  | 'day_change_pct'
  | 'cot_lev_money_net'
  | 'oi_delta'
  | 'created_at'
>;

export const TRACKED_PAIRS = ['EURUSD', 'USDJPY', 'USDINR'];

// getLatestRegimeCalls
export function useLatestRegimeCalls() {
  return useQuery({
    queryKey: ['regime_calls', 'latest'],
    queryFn: async (): Promise<Record<string, LatestRegimeCallRow>> => {
      const { data, error } = await supabase
        .from('regime_calls')
        .select('pair,date,regime,confidence,signal_composite,rate_signal,cot_signal,vol_signal,rr_signal,oi_signal,primary_driver,created_at')
        .in('pair', TRACKED_PAIRS)
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
  });
}

// getRegimeHeatmap
export function useRegimeHeatmap() {
  return useQuery({
    queryKey: ['regime_calls', 'heatmap'],
    queryFn: async (): Promise<{ date: string; pair: string; regime: string }[]> => {
      const d = new Date();
      d.setDate(d.getDate() - 30);
      const { data, error } = await supabase
        .from('regime_calls')
        .select('date, pair, regime')
        .in('pair', TRACKED_PAIRS)
        .gte('date', d.toISOString().split('T')[0])
        .order('date', { ascending: true });

      if (error) throw error;
      return (data as { date: string; pair: string; regime: string }[]) ?? [];
    },
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
  return useQuery({
    queryKey: ['signals', 'latest'],
    queryFn: async (): Promise<Record<string, LatestSignalRow>> => {
      const { data, error } = await supabase
        .from('signals')
        .select(
          'pair,date,spot,rate_diff_2y,rate_diff_10y,cot_percentile,realized_vol_20d,realized_vol_5d,implied_vol_30d,cross_asset_vix,cross_asset_dxy,cross_asset_oil,day_change_pct,cot_lev_money_net,oi_delta,created_at',
        )
        .in('pair', TRACKED_PAIRS)
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
  return useQuery({
    queryKey: ['validation_log', 'equity'],
    queryFn: async (): Promise<EquityRow[]> => {
      const { data, error } = await supabase
        .from('validation_log')
        .select('date, pair, actual_return_1d')
        .in('pair', TRACKED_PAIRS)
        .order('date', { ascending: true });
      if (error) throw error;
      return (data as EquityRow[]) ?? [];
    },
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

/** Deep historical daily OHLCV archive for MAX-range chart mode. */
export function useHistoricalData(pair: string, enabled = false) {
  return useQuery({
    queryKey: ['signals', 'historical', pair],
    queryFn: async (): Promise<
      Array<{ date: string; pair: string; open: number | null; high: number | null; low: number | null; close: number | null; volume: number | null }>
    > => {
      const { data, error } = await supabase
        .from('historical_prices')
        .select('date,pair,open,high,low,close,volume')
        .eq('pair', pair)
        .order('date', { ascending: true })
        .limit(25000);
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
