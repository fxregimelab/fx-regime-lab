import type { Database } from "./database.types";

type RegimeCallRow = Database["public"]["Tables"]["regime_calls"]["Row"];
type SignalRow = Database["public"]["Tables"]["signals"]["Row"];
type ValidationLogRow = Database["public"]["Tables"]["validation_log"]["Row"];
type BriefLogRow = Database["public"]["Tables"]["brief_log"]["Row"];

export interface LatestRegimeCall {
  pair: string;
  date: string;
  regime: string;
  confidence: number;
  signal_composite: number;
  rate_signal: string | null;
  primary_driver: string | null;
  created_at: string;
}

export interface LatestSignal {
  pair: string;
  date: string;
  spot: number | null;
  rate_diff_2y: number | null;
  cot_percentile: number | null;
  realized_vol_20d: number | null;
  realized_vol_5d: number | null;
  implied_vol_30d: number | null;
  day_change: number | null;
  day_change_pct: number | null;
  created_at: string;
}

export interface ValidationRow {
  date: string;
  pair: string;
  call: string;
  outcome: "correct" | "incorrect";
  return_pct: number;
}

function toLatestRegimeCall(row: RegimeCallRow): LatestRegimeCall {
  return {
    pair: row.pair,
    date: row.date,
    regime: row.regime,
    confidence: row.confidence,
    signal_composite: row.signal_composite,
    rate_signal: row.rate_signal,
    primary_driver: row.primary_driver,
    created_at: row.created_at,
  };
}

function toLatestSignal(row: SignalRow): LatestSignal {
  return {
    pair: row.pair,
    date: row.date,
    spot: row.spot,
    rate_diff_2y: row.rate_diff_2y,
    cot_percentile: row.cot_percentile,
    realized_vol_20d: row.realized_vol_20d,
    realized_vol_5d: row.realized_vol_5d,
    implied_vol_30d: row.implied_vol_30d,
    day_change: row.day_change,
    day_change_pct: row.day_change_pct,
    created_at: row.created_at,
  };
}

export async function getLatestRegimeCalls(
  supabase: any
): Promise<Record<string, LatestRegimeCall>> {
  const { data, error } = await supabase
    .from("regime_calls")
    .select("*")
    .order("date", { ascending: false })
    .limit(100);

  if (error || !data) return {};

  const latest: Record<string, LatestRegimeCall> = {};
  for (const row of data as RegimeCallRow[]) {
    const pair = row.pair;
    if (!latest[pair]) {
      latest[pair] = toLatestRegimeCall(row);
    }
  }
  return latest;
}

export async function getLatestSignals(
  supabase: any
): Promise<Record<string, LatestSignal>> {
  const { data, error } = await supabase
    .from("signals")
    .select("*")
    .order("date", { ascending: false })
    .limit(100);

  if (error || !data) return {};

  const latest: Record<string, LatestSignal> = {};
  for (const row of data as SignalRow[]) {
    const pair = row.pair;
    if (!latest[pair]) {
      latest[pair] = toLatestSignal(row);
    }
  }
  return latest;
}

export async function getValidationLog(
  supabase: any,
  limit = 500
): Promise<ValidationRow[]> {
  const { data, error } = await supabase
    .from("validation_log")
    .select("*")
    .order("date", { ascending: false })
    .limit(limit);

  if (error || !data) return [];

  const PAIR_DISPLAY: Record<string, string> = {
    EURUSD: "EUR/USD",
    USDJPY: "USD/JPY",
    USDINR: "USD/INR",
  };

  return (data as ValidationLogRow[])
    .filter((r) => r.correct_1d !== null && r.actual_return_1d != null)
    .map((r) => ({
      date: r.date,
      pair: PAIR_DISPLAY[r.pair] ?? r.pair,
      call: r.predicted_regime ?? "—",
      outcome: r.correct_1d ? "correct" : "incorrect",
      return_pct: Number(r.actual_return_1d),
    }));
}

export async function getLatestBrief(supabase: any): Promise<BriefLogRow | null> {
  const { data, error } = await supabase
    .from("brief_log")
    .select("*")
    .order("date", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (error) return null;
  return data as BriefLogRow | null;
}

export async function getHistoricalRegimeCalls(
  supabase: any,
  pair: string,
  limit = 30
) {
  const { data, error } = await supabase
    .from("regime_calls")
    .select("date,regime,confidence,signal_composite,primary_driver")
    .eq("pair", pair)
    .order("date", { ascending: false })
    .limit(limit);

  if (error || !data) return [];
  return data as Array<{
    date: string;
    regime: string;
    confidence: number;
    signal_composite: number;
    primary_driver: string | null;
  }>;
}

export async function getSignalHistory(
  supabase: any,
  pair: string,
  limit = 90
) {
  const { data, error } = await supabase
    .from("signals")
    .select("date,spot,rate_diff_2y,cot_percentile,realized_vol_20d")
    .eq("pair", pair)
    .order("date", { ascending: false })
    .limit(limit);

  if (error || !data) return [];
  return (data as Array<{
    date: string;
    spot: number | null;
    rate_diff_2y: number | null;
    cot_percentile: number | null;
    realized_vol_20d: number | null;
  }>).reverse();
}
