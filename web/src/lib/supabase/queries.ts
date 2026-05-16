import type { Database } from "./database.types";

type RegimeCallRow = Database["public"]["Tables"]["regime_calls"]["Row"];
type SignalRow = Database["public"]["Tables"]["signals"]["Row"];
type ValidationLogRow = Database["public"]["Tables"]["validation_log"]["Row"];
type ValidationStatsRow =
  Database["public"]["Tables"]["validation_stats"]["Row"];
export type BriefLogRow = Database["public"]["Tables"]["brief_log"]["Row"];
export type MacroEventRow = Database["public"]["Tables"]["macro_events"]["Row"];
type HistoricalPriceRow =
  Database["public"]["Tables"]["historical_prices"]["Row"];
type ResearchMemoRow = Database["public"]["Tables"]["research_memos"]["Row"];
type HealthCheckRow = Database["public"]["Tables"]["health_checks"]["Row"];

export interface LatestRegimeCall {
  pair: string;
  date: string;
  regime: string;
  confidence: number | null;
  signal_composite: number | null;
  rate_signal: string | null;
  primary_driver: string | null;
  special_signal_value: number | null;
  special_signal_label: string | null;
  model_version: string | null;
  data_quality_score: number | null;
  stress_level: string | null;
  created_at: string | null;
  predicted_direction: string | null;
  entry_timing: string | null;
  position_size: string | null;
  stop_level: number | null;
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
  cross_asset_us10y: number | null;
  realized_vol_rank: number | null;
  rate_z_tactical: number | null;
  rate_z_structural: number | null;
  rate_diff_10y_real: number | null;
  breakeven_inflation_10y: number | null;
  skew_alignment: number | null;
  risk_reversal_25d: number | null;
  fpi_flow: number | null;
  cot_net_pos: number | null;
  cot_asset_mgr_net: number | null;
  cot_lev_money_net: number | null;
  created_at: string | null;
}

export interface ValidationRow {
  date: string;
  pair: string;
  call: string;
  outcome: "correct" | "incorrect";
  return_pct: number;
}

export interface ValidationStats {
  pair: string;
  horizon: "t5" | "t20";
  winRate: number | null;
  brierScore: number | null;
  sampleSize: number | null;
  avgReturnBps: number | null;
  sharpeLike: number | null;
  rolling90dAccuracy: number | null;
  asOfDate: string;
}

export interface ValidationRowT5 {
  date: string;
  pair: string;
  predicted: string;
  t5ReturnBps: number | null;
  t5Outcome: "CORRECT" | "WRONG" | "NEUTRAL" | "—";
  t5Brier: number | null;
  t20ReturnBps: number | null;
  t20Outcome: "CORRECT" | "WRONG" | "NEUTRAL" | "—";
  t20Brier: number | null;
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
    special_signal_value: row.special_signal_value,
    special_signal_label: row.special_signal_label,
    model_version: row.model_version,
    data_quality_score: row.data_quality_score,
    stress_level: row.stress_level,
    created_at: row.created_at,
    predicted_direction: row.predicted_direction,
    entry_timing: row.entry_timing,
    position_size: row.position_size,
    stop_level: row.stop_level,
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
    cross_asset_us10y: row.cross_asset_us10y,
    realized_vol_rank: row.realized_vol_rank,
    rate_z_tactical: row.rate_z_tactical,
    rate_z_structural: row.rate_z_structural,
    rate_diff_10y_real: row.rate_diff_10y_real,
    breakeven_inflation_10y: row.breakeven_inflation_10y,
    skew_alignment: row.skew_alignment,
    risk_reversal_25d: row.risk_reversal_25d,
    fpi_flow: row.fpi_flow,
    cot_net_pos: row.cot_net_pos,
    cot_asset_mgr_net: row.cot_asset_mgr_net,
    cot_lev_money_net: row.cot_lev_money_net,
    created_at: row.created_at,
  };
}

import type { createClient } from "./server";

type TypedSupabaseClient = Awaited<ReturnType<typeof createClient>>;

export async function getLatestRegimeCalls(
  supabase: TypedSupabaseClient,
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
  supabase: TypedSupabaseClient,
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
  supabase: TypedSupabaseClient,
  limit = 500,
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

export async function getLatestBrief(
  supabase: TypedSupabaseClient,
): Promise<BriefLogRow | null> {
  const { data, error } = await supabase
    .from("brief_log")
    .select("*")
    .order("date", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (error) return null;
  return data as BriefLogRow | null;
}

export async function getValidationStats(
  supabase: TypedSupabaseClient,
  horizon: "t5" | "t20",
): Promise<ValidationStats[]> {
  const { data, error } = await supabase
    .from("validation_stats")
    .select("*")
    .order("as_of_date", { ascending: false })
    .limit(100);

  if (error || !data) return [];

  const rows = data as ValidationStatsRow[];
  // Get latest as_of_date
  const latestDate = rows[0]?.as_of_date;
  if (!latestDate) return [];

  // Filter to latest date only
  const latest = rows.filter((r) => r.as_of_date === latestDate);

  const prefix = horizon === "t5" ? "t5" : "t20";
  const mapRow = (r: ValidationStatsRow): ValidationStats => ({
    pair: r.pair,
    horizon,
    winRate: r[`${prefix}_win_rate` as keyof ValidationStatsRow] as
      | number
      | null,
    brierScore: r[`${prefix}_mean_brier` as keyof ValidationStatsRow] as
      | number
      | null,
    sampleSize: r[`${prefix}_total_calls` as keyof ValidationStatsRow] as
      | number
      | null,
    avgReturnBps: r[
      `${prefix}_mean_log_return_bps` as keyof ValidationStatsRow
    ] as number | null,
    sharpeLike: r[`${prefix}_sharpe_like` as keyof ValidationStatsRow] as
      | number
      | null,
    rolling90dAccuracy: r[
      `${prefix}_rolling_90d_accuracy` as keyof ValidationStatsRow
    ] as number | null,
    asOfDate: r.as_of_date,
  });

  return latest.map(mapRow);
}

export async function getValidationLogT5T20(
  supabase: TypedSupabaseClient,
  limit = 500,
): Promise<ValidationRowT5[]> {
  const { data, error } = await supabase
    .from("validation_log")
    .select("*")
    .not("brier_score_t5", "is", null)
    .order("date", { ascending: false })
    .limit(limit);

  if (error || !data) return [];

  const PAIR_DISPLAY: Record<string, string> = {
    EURUSD: "EUR/USD",
    USDJPY: "USD/JPY",
    USDINR: "USD/INR",
  };

  return (data as ValidationLogRow[]).map((r) => ({
    date: r.date,
    pair: PAIR_DISPLAY[r.pair] ?? r.pair,
    predicted: r.predicted_direction ?? "—",
    t5ReturnBps: r.log_return_t5_bps,
    t5Outcome: r.correct_t5
      ? "CORRECT"
      : r.actual_direction_t5 === "NEUTRAL"
        ? "NEUTRAL"
        : r.actual_direction_t5 != null
          ? "WRONG"
          : "—",
    t5Brier: r.brier_score_t5,
    t20ReturnBps: r.log_return_t20_bps,
    t20Outcome: r.correct_t20
      ? "CORRECT"
      : r.actual_direction_t20 === "NEUTRAL"
        ? "NEUTRAL"
        : r.actual_direction_t20 != null
          ? "WRONG"
          : "—",
    t20Brier: r.brier_score_t20,
  }));
}

export async function getValidationLogForPair(
  supabase: TypedSupabaseClient,
  pair: string,
  limit = 200,
): Promise<ValidationRowT5[]> {
  const PAIR_CODE: Record<string, string> = {
    "EUR/USD": "EURUSD",
    "USD/JPY": "USDJPY",
    "USD/INR": "USDINR",
  };
  const code = PAIR_CODE[pair] ?? pair;

  const { data, error } = await supabase
    .from("validation_log")
    .select("*")
    .eq("pair", code)
    .not("brier_score_t5", "is", null)
    .order("date", { ascending: false })
    .limit(limit);

  if (error || !data) return [];

  const PAIR_DISPLAY: Record<string, string> = {
    EURUSD: "EUR/USD",
    USDJPY: "USD/JPY",
    USDINR: "USD/INR",
  };

  return (data as ValidationLogRow[]).map((r) => ({
    date: r.date,
    pair: PAIR_DISPLAY[r.pair] ?? r.pair,
    predicted: r.predicted_direction ?? "—",
    t5ReturnBps: r.log_return_t5_bps,
    t5Outcome: r.correct_t5
      ? "CORRECT"
      : r.actual_direction_t5 === "NEUTRAL"
        ? "NEUTRAL"
        : r.actual_direction_t5 != null
          ? "WRONG"
          : "—",
    t5Brier: r.brier_score_t5,
    t20ReturnBps: r.log_return_t20_bps,
    t20Outcome: r.correct_t20
      ? "CORRECT"
      : r.actual_direction_t20 === "NEUTRAL"
        ? "NEUTRAL"
        : r.actual_direction_t20 != null
          ? "WRONG"
          : "—",
    t20Brier: r.brier_score_t20,
  }));
}

export async function getHistoricalRegimeCalls(
  supabase: TypedSupabaseClient,
  pair: string,
  limit = 30,
) {
  const { data, error } = await supabase
    .from("regime_calls")
    .select(
      "date,regime,confidence,signal_composite,primary_driver,rate_signal,entry_timing,position_size,stop_level,created_at,predicted_direction",
    )
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
    rate_signal: string | null;
    entry_timing: string | null;
    position_size: string | null;
    stop_level: number | null;
    created_at: string | null;
    predicted_direction: string | null;
  }>;
}

export async function getSignalHistory(
  supabase: TypedSupabaseClient,
  pair: string,
  limit = 90,
) {
  const { data, error } = await supabase
    .from("signals")
    .select("date,spot,rate_diff_2y,cot_percentile,realized_vol_20d")
    .eq("pair", pair)
    .order("date", { ascending: false })
    .limit(limit);

  if (error || !data) return [];
  return (
    data as Array<{
      date: string;
      spot: number | null;
      rate_diff_2y: number | null;
      cot_percentile: number | null;
      realized_vol_20d: number | null;
    }>
  ).reverse();
}

export interface PairValidationSummary {
  t5WinRate: number | null;
  t5Brier: number | null;
  t5SampleSize: number | null;
  t5SharpeLike: number | null;
  t20WinRate: number | null;
  t20Brier: number | null;
  t20SampleSize: number | null;
  t20SharpeLike: number | null;
}

export async function getPairValidationSummary(
  supabase: TypedSupabaseClient,
  pair: string,
): Promise<PairValidationSummary | null> {
  const { data, error } = await supabase
    .from("validation_stats")
    .select("*")
    .eq("pair", pair)
    .order("as_of_date", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (error || !data) return null;

  const row = data as ValidationStatsRow;
  return {
    t5WinRate: row.t5_win_rate,
    t5Brier: row.t5_mean_brier,
    t5SampleSize: row.t5_total_calls,
    t5SharpeLike: row.t5_sharpe_like,
    t20WinRate: row.t20_win_rate,
    t20Brier: row.t20_mean_brier,
    t20SampleSize: row.t20_total_calls,
    t20SharpeLike: row.t20_sharpe_like,
  };
}

export interface PairValidationHistoryItem {
  date: string;
  predicted: string;
  t5Outcome: string;
  t5ReturnBps: number | null;
  t5Brier: number | null;
  t20Outcome: string;
  t20ReturnBps: number | null;
  t20Brier: number | null;
}

export async function getPairValidationHistory(
  supabase: TypedSupabaseClient,
  pair: string,
  limit = 20,
): Promise<PairValidationHistoryItem[]> {
  const { data, error } = await supabase
    .from("validation_log")
    .select("*")
    .eq("pair", pair)
    .not("brier_score_t5", "is", null)
    .order("date", { ascending: false })
    .limit(limit);

  if (error || !data) return [];

  return (data as ValidationLogRow[]).map((r) => ({
    date: r.date,
    predicted: r.predicted_direction ?? "—",
    t5Outcome: r.correct_t5
      ? "CORRECT"
      : r.actual_direction_t5 === "NEUTRAL"
        ? "NEUTRAL"
        : r.actual_direction_t5 != null
          ? "WRONG"
          : "—",
    t5ReturnBps: r.log_return_t5_bps,
    t5Brier: r.brier_score_t5,
    t20Outcome: r.correct_t20
      ? "CORRECT"
      : r.actual_direction_t20 === "NEUTRAL"
        ? "NEUTRAL"
        : r.actual_direction_t20 != null
          ? "WRONG"
          : "—",
    t20ReturnBps: r.log_return_t20_bps,
    t20Brier: r.brier_score_t20,
  }));
}

export async function getHistoricalPrices(
  supabase: TypedSupabaseClient,
  pair: string,
  limit = 30,
): Promise<{ date: string; close: number }[]> {
  const { data, error } = await supabase
    .from("historical_prices")
    .select("date,close")
    .eq("pair", pair)
    .order("date", { ascending: false })
    .limit(limit);

  if (error || !data) return [];
  return (data as HistoricalPriceRow[])
    .filter((r) => r.close != null)
    .map((r) => ({ date: r.date, close: r.close as number }))
    .reverse();
}

export interface CrossAssetSnapshot {
  vix: { value: number | null; change: number | null };
  dxy: { value: number | null; change: number | null };
  oil: { value: number | null; change: number | null };
  gold: { value: number | null; change: number | null };
  copper: { value: number | null; change: number | null };
  stoxx: { value: number | null; change: number | null };
  us10y: { value: number | null; change: number | null };
}

export async function getCrossAssetSnapshot(
  supabase: TypedSupabaseClient,
): Promise<CrossAssetSnapshot> {
  const { data, error } = await supabase
    .from("signals")
    .select(
      "date,cross_asset_vix,cross_asset_dxy,cross_asset_oil,cross_asset_gold,cross_asset_copper,cross_asset_stoxx,cross_asset_us10y",
    )
    .order("date", { ascending: false })
    .limit(6);

  if (error || !data || data.length === 0) {
    return {
      vix: { value: null, change: null },
      dxy: { value: null, change: null },
      oil: { value: null, change: null },
      gold: { value: null, change: null },
      copper: { value: null, change: null },
      stoxx: { value: null, change: null },
      us10y: { value: null, change: null },
    };
  }

  const rows = data as SignalRow[];
  const latestDate = rows[0].date;
  const latestRow = rows.find((r) => r.date === latestDate) ?? rows[0];

  const prevRow = rows.find((r) => r.date !== latestDate);

  const compute = (key: keyof SignalRow) => {
    const curr = latestRow[key] as number | null;
    const prev = prevRow ? (prevRow[key] as number | null) : null;
    const change = curr != null && prev != null ? curr - prev : null;
    return { value: curr, change };
  };

  return {
    vix: compute("cross_asset_vix"),
    dxy: compute("cross_asset_dxy"),
    oil: compute("cross_asset_oil"),
    gold: compute("cross_asset_gold"),
    copper: compute("cross_asset_copper"),
    stoxx: compute("cross_asset_stoxx"),
    us10y: compute("cross_asset_us10y"),
  };
}

export async function getMacroEventsToday(
  supabase: TypedSupabaseClient,
): Promise<MacroEventRow[]> {
  const today = new Date().toISOString().slice(0, 10);
  const { data, error } = await supabase
    .from("macro_events")
    .select("*")
    .eq("date", today)
    .eq("impact", "HIGH")
    .order("event", { ascending: true });

  if (error || !data) return [];
  return data as MacroEventRow[];
}

export async function getSignalHistoryForAllPairs(
  supabase: TypedSupabaseClient,
  limit = 30,
): Promise<Record<string, SignalRow[]>> {
  const { data, error } = await supabase
    .from("signals")
    .select("*")
    .order("date", { ascending: false })
    .limit(limit * 3);

  if (error || !data) return {};

  const result: Record<string, SignalRow[]> = {};
  for (const row of data as SignalRow[]) {
    const arr = result[row.pair] ?? [];
    arr.push(row);
    result[row.pair] = arr;
  }
  // Ensure each pair's array is sorted ascending for sparklines
  for (const pair of Object.keys(result)) {
    result[pair].sort((a, b) => a.date.localeCompare(b.date));
  }
  return result;
}

export async function getResearchMemosList(
  supabase: TypedSupabaseClient,
  limit = 50,
): Promise<Pick<ResearchMemoRow, "id" | "date" | "title" | "link_url">[]> {
  const { data, error } = await supabase
    .from("research_memos")
    .select("id, date, title, link_url")
    .order("date", { ascending: false })
    .limit(limit);

  if (error || !data) return [];
  return data as Pick<ResearchMemoRow, "id" | "date" | "title" | "link_url">[];
}

export async function getResearchMemoByDate(
  supabase: TypedSupabaseClient,
  date: string,
): Promise<ResearchMemoRow | null> {
  const { data, error } = await supabase
    .from("research_memos")
    .select("*")
    .eq("date", date)
    .maybeSingle();

  if (error) return null;
  return data as ResearchMemoRow | null;
}

/* ─── Pipeline Health ───────────────────────────────────────────────────── */

export interface PipelineDayHealth {
  date: string;
  status: "HEALTHY" | "DEGRADED" | "FAILED" | "UNKNOWN";
  dqs: number | null;
  regimeCallsCount: number;
  stepsCompleted: string[];
  stepsFailed: string[];
  validationComputed: boolean;
  aiBriefsGenerated: boolean;
  errors: string[];
}

function inferStatusFromHealthCheck(row: HealthCheckRow): PipelineDayHealth["status"] {
  if (row.completed_at == null) return "FAILED";
  const dqs = row.data_quality_score ?? 0;
  const pairs = row.pairs_published ?? 0;
  const failed = row.sources_failed ?? 0;
  if (pairs >= 3 && dqs >= 0.8 && failed === 0) return "HEALTHY";
  if (pairs >= 3 && dqs >= 0.5) return "DEGRADED";
  if (pairs === 0 && dqs === 0) return "UNKNOWN";
  return "FAILED";
}

export async function getPipelineHealth(
  supabase: TypedSupabaseClient,
  days = 14,
): Promise<PipelineDayHealth[]> {
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);
  const cutoffStr = cutoff.toISOString().slice(0, 10);

  // Try health_checks first
  const { data: healthData, error: healthError } = await supabase
    .from("health_checks")
    .select("*")
    .gte("pipeline_date", cutoffStr)
    .order("pipeline_date", { ascending: false })
    .limit(100);

  if (!healthError && healthData && healthData.length > 0) {
    return (healthData as HealthCheckRow[]).map((row) => {
      const status = inferStatusFromHealthCheck(row);
      const errors: string[] = [];
      if (row.error_log) errors.push(row.error_log);
      const stepsCompleted: string[] = [];
      const stepsFailed: string[] = [];
      if (row.completed_at) {
        stepsCompleted.push("Pipeline completion");
      } else {
        stepsFailed.push("Pipeline completion");
      }
      if ((row.pairs_published ?? 0) >= 3) {
        stepsCompleted.push("Pair publication");
      } else {
        stepsFailed.push("Pair publication");
      }
      if ((row.data_quality_score ?? 0) >= 0.8) {
        stepsCompleted.push("Data quality gate");
      } else {
        stepsFailed.push("Data quality gate");
      }
      return {
        date: row.pipeline_date,
        status,
        dqs: row.data_quality_score,
        regimeCallsCount: row.pairs_published ?? 0,
        stepsCompleted,
        stepsFailed,
        validationComputed: status !== "FAILED" && status !== "UNKNOWN",
        aiBriefsGenerated: status === "HEALTHY",
        errors,
      };
    });
  }

  // Fallback: infer from data presence
  const [{ data: callsData }, { data: signalsData }, { data: briefData }, { data: valStatsData }] =
    await Promise.all([
      supabase
        .from("regime_calls")
        .select("date,pair")
        .gte("date", cutoffStr)
        .order("date", { ascending: false }),
      supabase
        .from("signals")
        .select("date,pair")
        .gte("date", cutoffStr)
        .order("date", { ascending: false }),
      supabase
        .from("brief_log")
        .select("date")
        .gte("date", cutoffStr)
        .order("date", { ascending: false }),
      supabase
        .from("validation_stats")
        .select("as_of_date,pair")
        .gte("as_of_date", cutoffStr)
        .order("as_of_date", { ascending: false }),
    ]);

  // Build date map
  const dateMap = new Map<string, PipelineDayHealth>();

  // Initialize all dates in range
  for (let i = 0; i < days; i++) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().slice(0, 10);
    dateMap.set(dateStr, {
      date: dateStr,
      status: "UNKNOWN",
      dqs: null,
      regimeCallsCount: 0,
      stepsCompleted: [],
      stepsFailed: [],
      validationComputed: false,
      aiBriefsGenerated: false,
      errors: [],
    });
  }

  // Aggregate regime_calls per date
  for (const row of (callsData ?? []) as Array<{ date: string; pair: string }>) {
    const day = dateMap.get(row.date);
    if (day) {
      day.regimeCallsCount += 1;
    }
  }

  // Aggregate signals per date
  const signalDates = new Set<string>();
  for (const row of (signalsData ?? []) as Array<{ date: string; pair: string }>) {
    signalDates.add(row.date);
  }

  // Aggregate briefs per date
  const briefDates = new Set<string>();
  for (const row of (briefData ?? []) as Array<{ date: string }>) {
    briefDates.add(row.date);
  }

  // Aggregate validation stats per date
  const valDates = new Set<string>();
  for (const row of (valStatsData ?? []) as Array<{ as_of_date: string; pair: string }>) {
    valDates.add(row.as_of_date);
  }

  // Determine status for each date
  for (const day of dateMap.values()) {
    const hasSignals = signalDates.has(day.date);
    const hasCalls = day.regimeCallsCount > 0;
    const hasBrief = briefDates.has(day.date);
    const hasValidation = valDates.has(day.date);

    day.stepsCompleted = [];
    day.stepsFailed = [];

    if (hasSignals) day.stepsCompleted.push("Data ingestion");
    else day.stepsFailed.push("Data ingestion");

    if (hasCalls) day.stepsCompleted.push("Regime inference");
    else day.stepsFailed.push("Regime inference");

    if (hasValidation) {
      day.stepsCompleted.push("Validation");
      day.validationComputed = true;
    } else {
      day.stepsFailed.push("Validation");
      day.validationComputed = false;
    }

    if (hasBrief) {
      day.stepsCompleted.push("AI briefs");
      day.aiBriefsGenerated = true;
    } else {
      day.stepsFailed.push("AI briefs");
      day.aiBriefsGenerated = false;
    }

    // Infer DQS from regime_calls if available
    if (hasCalls && hasSignals) {
      day.dqs = day.regimeCallsCount >= 3 ? 0.95 : 0.7;
    } else if (hasCalls || hasSignals) {
      day.dqs = 0.5;
    }

    if (hasSignals && hasCalls && hasValidation && hasBrief) {
      day.status = "HEALTHY";
    } else if (hasSignals || hasCalls) {
      day.status = "DEGRADED";
    } else if (hasBrief || hasValidation) {
      day.status = "DEGRADED";
    } else {
      day.status = "UNKNOWN";
    }
  }

  return Array.from(dateMap.values()).sort((a, b) => b.date.localeCompare(a.date));
}

export interface AccuracyAlert {
  pair: string;
  accuracy: number;
  threshold: number;
  severity: "critical" | "warning";
}

export async function getLatestAccuracyAlerts(
  supabase: TypedSupabaseClient,
): Promise<AccuracyAlert[]> {
  const { data, error } = await supabase
    .from("validation_stats")
    .select("*")
    .order("as_of_date", { ascending: false })
    .limit(20);

  if (error || !data) return [];

  const rows = data as ValidationStatsRow[];
  const latestDate = rows[0]?.as_of_date;
  if (!latestDate) return [];

  const latest = rows.filter((r) => r.as_of_date === latestDate && r.pair !== "ALL");
  const alerts: AccuracyAlert[] = [];

  for (const row of latest) {
    const acc = row.t5_rolling_90d_accuracy ?? row.t20_rolling_90d_accuracy ?? null;
    if (acc == null) continue;

    if (acc < 0.5) {
      alerts.push({
        pair: row.pair,
        accuracy: acc,
        threshold: 0.5,
        severity: "critical",
      });
    } else if (row.pair === "EURUSD" && acc < 0.55) {
      alerts.push({
        pair: row.pair,
        accuracy: acc,
        threshold: 0.55,
        severity: "warning",
      });
    }
  }

  return alerts;
}
