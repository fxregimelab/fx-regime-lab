import { DEFAULT_ACCURACY_GATE, EURUSD_ACCURACY_GATE } from "@/lib/config";
import {
  DataSource,
  LIVE_CUTOFF_DATE,
  applyDataSourceDateFilter,
} from "@/lib/data/adapters/data-source";
import { toLegacyRegimeCall } from "@/lib/data/adapters/supabase-validation-adapter";
import type { RegimeCall } from "@/lib/data/domain/regime";
import type {
  ValidationStats as DomainValidationStats,
  RegimeBreakdownEntry,
  ValidationEntry,
} from "@/lib/data/domain/validation";
import {
  formatRegimeLabel,
  toLegacyOutcome,
} from "@/lib/data/presentation/outcomes";
import { formatPairCode } from "@/lib/data/presentation/pairs";
import { RegimeCallRepository } from "@/lib/data/repositories/regime-call-repository";
import { ValidationRepository } from "@/lib/data/repositories/validation-repository";
import type { Database } from "./database.types";

type RegimeCallRow = Database["public"]["Tables"]["regime_calls"]["Row"];
type SignalRow = Database["public"]["Tables"]["signals"]["Row"];
type ValidationLogRow = Database["public"]["Tables"]["validation_log"]["Row"];
type ValidationStatsRow =
  Database["public"]["Tables"]["validation_stats"]["Row"];
export type BriefLogRow = Database["public"]["Tables"]["brief_log"]["Row"];
export type MacroEventRow = Database["public"]["Tables"]["macro_events"]["Row"];
export type SiteContentRow =
  Database["public"]["Tables"]["site_content"]["Row"];
export type SiteSettingsRow =
  Database["public"]["Tables"]["site_settings"]["Row"];
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
  cot_signal: string | null;
  vol_signal: string | null;
  rr_signal: string | null;
  oi_signal: string | null;
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
  z_blended: number | null;
  rate_diff_10y_real: number | null;
  breakeven_inflation_10y: number | null;
  skew_alignment: number | null;
  risk_reversal_25d: number | null;
  fpi_flow: number | null;
  cot_net_pos: number | null;
  cot_asset_mgr_net: number | null;
  cot_lev_money_net: number | null;
  india_vix: number | null;
  inr_forward_premium: number | null;
  oi_delta: number | null;
  volume_rvol: number | null;
  structural_instability: boolean;
  ecb_balance_sheet: number | null;
  bund_btp_spread: number | null;
  boj_policy_rate: number | null;
  created_at: string | null;
}

export interface ValidationRow {
  date: string;
  pair: string;
  call: string;
  outcome: "correct" | "incorrect" | "neutral";
  return_pct: number;
}

export type ValidationStats = DomainValidationStats;

export type ValidationRowT5 = ValidationEntry;

function toLatestRegimeCall(call: RegimeCall): LatestRegimeCall {
  return toLegacyRegimeCall(call);
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
    z_blended: row.z_blended ?? null,
    rate_diff_10y_real: row.rate_diff_10y_real,
    breakeven_inflation_10y: row.breakeven_inflation_10y,
    skew_alignment: row.skew_alignment,
    risk_reversal_25d: row.risk_reversal_25d,
    fpi_flow: row.fpi_flow,
    cot_net_pos: row.cot_net_pos,
    cot_asset_mgr_net: row.cot_asset_mgr_net,
    cot_lev_money_net: row.cot_lev_money_net,
    india_vix: row.india_vix ?? null,
    inr_forward_premium: row.inr_forward_premium ?? null,
    oi_delta: row.oi_delta ?? null,
    volume_rvol: row.volume_rvol ?? null,
    structural_instability: row.structural_instability ?? false,
    ecb_balance_sheet: row.ecb_balance_sheet ?? null,
    bund_btp_spread: row.bund_btp_spread ?? null,
    boj_policy_rate: row.boj_policy_rate ?? null,
    created_at: row.created_at,
  };
}

import type { createClient } from "./server";

type TypedSupabaseClient = Awaited<ReturnType<typeof createClient>>;

export async function getLatestRegimeCalls(
  supabase: TypedSupabaseClient,
): Promise<Record<string, LatestRegimeCall>> {
  const latest = await RegimeCallRepository.getLatest(supabase);
  const result: Record<string, LatestRegimeCall> = {};
  for (const [pair, call] of Object.entries(latest)) {
    result[pair] = toLatestRegimeCall(call);
  }
  return result;
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
  limit = 100,
  dataSource: DataSource = DataSource.Live,
): Promise<ValidationRow[]> {
  // Try joined query first to fetch regime call labels
  let q = supabase
    .from("validation_log")
    .select("*, regime_calls!fk_validation_log_call_id(regime)")
    .eq("is_superseded", false)
    .order("date", { ascending: false })
    .limit(limit);

  q = applyDataSourceDateFilter(q, dataSource);

  const { data, error } = await q;

  if (!error && data) {
    return (data as (ValidationLogRow & { regime_calls: { regime: string } })[])
      .filter((r) => r.correct_t5 !== null)
      .map((r) => ({
        date: r.date,
        pair: formatPairCode(r.pair),
        call: formatRegimeLabel(r.regime_calls?.regime),
        outcome: toLegacyOutcome(r.correct_t5, r.actual_direction_t5),
        return_pct: Number(r.log_return_t5_bps ?? 0),
      }));
  }

  // Fallback: plain validation_log without join
  let q2 = supabase
    .from("validation_log")
    .select("*")
    .eq("is_superseded", false)
    .order("date", { ascending: false })
    .limit(limit);

  q2 = applyDataSourceDateFilter(q2, dataSource);

  const { data: fallback, error: fallbackErr } = await q2;

  if (fallbackErr || !fallback) return [];

  return (fallback as ValidationLogRow[])
    .filter((r) => r.correct_t5 !== null)
    .map((r) => ({
      date: r.date,
      pair: formatPairCode(r.pair),
      call: "—",
      outcome: toLegacyOutcome(r.correct_t5, r.actual_direction_t5),
      return_pct: Number(r.log_return_t5_bps ?? 0),
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
  dataSource: DataSource = DataSource.Live,
): Promise<ValidationStats[]> {
  return ValidationRepository.getStats(supabase, horizon, dataSource);
}

export async function getValidationLogT5T20(
  supabase: TypedSupabaseClient,
  limit = 100,
  dataSource: DataSource = DataSource.Live,
): Promise<ValidationRowT5[]> {
  return ValidationRepository.getLogT5T20(supabase, limit, dataSource);
}

export type RegimeBreakdownRow = RegimeBreakdownEntry;

export async function getRegimeBreakdown(
  supabase: TypedSupabaseClient,
  limit = 100,
  dataSource: DataSource = DataSource.Live,
): Promise<RegimeBreakdownRow[]> {
  return ValidationRepository.getBreakdown(supabase, limit, dataSource);
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

  // Fetch validation_log rows (current versions only)
  const { data: valData, error: valError } = await supabase
    .from("validation_log")
    .select("*")
    .eq("pair", code)
    .eq("is_superseded", false)
    .not("brier_score_t5", "is", null)
    .order("date", { ascending: false })
    .limit(limit);

  if (valError || !valData) return [];

  // Fetch predicted_direction from regime_calls via call_id
  const callIds = (valData as ValidationLogRow[])
    .map((r) => r.call_id)
    .filter((id): id is number => id != null);

  const predictedMap = new Map<number, string>();
  if (callIds.length > 0) {
    const { data: regimeData } = await supabase
      .from("regime_calls")
      .select("id, predicted_direction")
      .in("id", callIds);
    for (const rc of (regimeData ?? []) as Array<{
      id: number | null;
      predicted_direction: string | null;
    }>) {
      if (rc.id != null && rc.predicted_direction) {
        predictedMap.set(rc.id, rc.predicted_direction);
      }
    }
  }

  const PAIR_DISPLAY: Record<string, string> = {
    EURUSD: "EUR/USD",
    USDJPY: "USD/JPY",
    USDINR: "USD/INR",
  };

  return (valData as ValidationLogRow[]).map((r) => ({
    date: r.date,
    pair: PAIR_DISPLAY[r.pair] ?? r.pair,
    predicted: r.call_id != null ? (predictedMap.get(r.call_id) ?? "—") : "—",
    t5ReturnBps: r.log_return_t5_bps,
    t5ReturnNetBps:
      (r as ValidationLogRow & { log_return_net_bps_t5: number | null })
        .log_return_net_bps_t5 ?? null,
    t5Outcome: r.correct_t5
      ? "CORRECT"
      : r.actual_direction_t5 === "NEUTRAL"
        ? "NEUTRAL"
        : r.actual_direction_t5 != null
          ? "WRONG"
          : "—",
    t5CorrectNet:
      (r as ValidationLogRow & { correct_net_t5: boolean | null })
        .correct_net_t5 ?? null,
    t5CostBps:
      (r as ValidationLogRow & { cost_bps_t5: number | null }).cost_bps_t5 ??
      null,
    t5Brier: r.brier_score_t5,
    t20ReturnBps: r.log_return_t20_bps,
    t20ReturnNetBps:
      (r as ValidationLogRow & { log_return_net_bps_t20: number | null })
        .log_return_net_bps_t20 ?? null,
    t20Outcome: r.correct_t20
      ? "CORRECT"
      : r.actual_direction_t20 === "NEUTRAL"
        ? "NEUTRAL"
        : r.actual_direction_t20 != null
          ? "WRONG"
          : "—",
    t20CorrectNet:
      (r as ValidationLogRow & { correct_net_t20: boolean | null })
        .correct_net_t20 ?? null,
    t20CostBps:
      (r as ValidationLogRow & { cost_bps_t20: number | null }).cost_bps_t20 ??
      null,
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
    .select(
      "date,spot,rate_diff_2y,cot_percentile,realized_vol_20d,realized_vol_5d,implied_vol_30d,day_change,day_change_pct,cross_asset_us10y,realized_vol_rank,rate_z_tactical,rate_z_structural,z_blended,rate_diff_10y_real,breakeven_inflation_10y,skew_alignment,risk_reversal_25d,fpi_flow,cot_net_pos,cot_asset_mgr_net,cot_lev_money_net,india_vix,inr_forward_premium,oi_delta,volume_rvol,structural_instability,ecb_balance_sheet,bund_btp_spread,boj_policy_rate",
    )
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
    .eq("is_superseded", false)
    .not("brier_score_t5", "is", null)
    .order("date", { ascending: false })
    .limit(limit);

  if (error || !data) return [];

  return (data as ValidationLogRow[]).map((r) => ({
    date: r.date,
    predicted: "—",
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
    .limit(90);

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

function inferStatusFromHealthCheck(
  row: HealthCheckRow,
): PipelineDayHealth["status"] {
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
  const [
    { data: callsData },
    { data: signalsData },
    { data: briefData },
    { data: valStatsData },
  ] = await Promise.all([
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
  for (const row of (callsData ?? []) as Array<{
    date: string;
    pair: string;
  }>) {
    const day = dateMap.get(row.date);
    if (day) {
      day.regimeCallsCount += 1;
    }
  }

  // Aggregate signals per date
  const signalDates = new Set<string>();
  for (const row of (signalsData ?? []) as Array<{
    date: string;
    pair: string;
  }>) {
    signalDates.add(row.date);
  }

  // Aggregate briefs per date
  const briefDates = new Set<string>();
  for (const row of (briefData ?? []) as Array<{ date: string }>) {
    briefDates.add(row.date);
  }

  // Aggregate validation stats per date
  const valDates = new Set<string>();
  for (const row of (valStatsData ?? []) as Array<{
    as_of_date: string;
    pair: string;
  }>) {
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

  return Array.from(dateMap.values()).sort((a, b) =>
    b.date.localeCompare(a.date),
  );
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
    .gte("as_of_date", LIVE_CUTOFF_DATE)
    .order("as_of_date", { ascending: false })
    .limit(20);

  if (error || !data) return [];

  const rows = data as ValidationStatsRow[];
  const latestDate = rows[0]?.as_of_date;
  if (!latestDate) return [];

  const latest = rows.filter(
    (r) => r.as_of_date === latestDate && r.pair !== "ALL",
  );
  const alerts: AccuracyAlert[] = [];

  for (const row of latest) {
    const acc =
      row.t5_rolling_90d_accuracy ?? row.t20_rolling_90d_accuracy ?? null;
    if (acc == null) continue;

    const gate =
      row.pair === "EURUSD" ? EURUSD_ACCURACY_GATE : DEFAULT_ACCURACY_GATE;
    if (acc < gate) {
      alerts.push({
        pair: row.pair,
        accuracy: acc,
        threshold: gate,
        severity: acc < DEFAULT_ACCURACY_GATE ? "critical" : "warning",
      });
    }
  }

  return alerts;
}

/* ─── Backtest / Versioned Queries ─────────────────────────────────────── */

export async function getBacktestVersions(
  supabase: TypedSupabaseClient,
): Promise<string[]> {
  const { data, error } = await supabase
    .from("backtest_versions")
    .select("version")
    .eq("is_public", true)
    .order("version", { ascending: false });

  if (error || !data) return ["v2"];
  const versions = (data as Array<{ version: string | null }>)
    .map((r) => r.version)
    .filter((v): v is string => v != null);
  return versions.length > 0 ? versions : ["v2"];
}

export interface VersionedRegimeCall {
  id: number;
  pair: string;
  date: string;
  regime: string;
  confidence: number | null;
  signal_composite: number | null;
  predicted_direction: string | null;
  primary_driver: string | null;
  model_version: string | null;
  rate_signal: string | null;
  cot_signal: string | null;
  vol_signal: string | null;
  rr_signal: string | null;
  oi_signal: string | null;
  entry_timing: string | null;
  created_at: string | null;
}

export async function getRegimeCallsByVersion(
  supabase: TypedSupabaseClient,
  version: string,
  pair?: string,
  dateRange?: { from: string; to: string },
  limit = 100,
): Promise<VersionedRegimeCall[]> {
  let q = supabase
    .from("regime_calls")
    .select(
      "id,pair,date,regime,confidence,signal_composite,predicted_direction,primary_driver,model_version,rate_signal,cot_signal,vol_signal,rr_signal,oi_signal,entry_timing,created_at",
    )
    .eq("model_version", version)
    .order("date", { ascending: false })
    .limit(limit);

  if (pair) q = q.eq("pair", pair);
  if (dateRange) {
    q = q.gte("date", dateRange.from).lte("date", dateRange.to);
  }

  const { data, error } = await q;
  if (error || !data) return [];
  return data as VersionedRegimeCall[];
}

export async function getCallRationale(
  supabase: TypedSupabaseClient,
  callId: number,
): Promise<VersionedRegimeCall | null> {
  const { data, error } = await supabase
    .from("regime_calls")
    .select(
      "id,pair,date,regime,confidence,signal_composite,predicted_direction,primary_driver,model_version,rate_signal,cot_signal,vol_signal,rr_signal,oi_signal,entry_timing,created_at",
    )
    .eq("id", callId)
    .single();

  if (error || !data) return null;
  return data as VersionedRegimeCall;
}

export interface SimulationResult {
  pair: string;
  sizingMethod: string;
  algorithm: string;
  sharpe: number | null;
  sortino: number | null;
  winRate: number | null;
  nTrades: number | null;
  turnover: number | null;
  totalPnl: number | null;
  meanBrier: number | null;
  maxDrawdownPct: number | null;
  params: Record<string, unknown>;
}

export async function getSimulationResults(
  supabase: TypedSupabaseClient,
  version: string,
): Promise<SimulationResult[]> {
  const { data, error } = await supabase
    .from("simulation_results")
    .select("pair, simulation_params, max_drawdown_pct")
    .eq("strategy_version", version)
    .limit(100);

  if (error || !data) return [];

  const seen = new Set<string>();
  const results: SimulationResult[] = [];

  for (const row of data as Array<{
    pair: string;
    simulation_params: Record<string, unknown> | null;
    max_drawdown_pct: number | null;
  }>) {
    const params = row.simulation_params ?? {};
    const key = `${row.pair}-${params.sizing_method ?? "unknown"}`;
    if (seen.has(key)) continue;
    seen.add(key);

    results.push({
      pair: row.pair,
      sizingMethod: String(params.sizing_method ?? "—"),
      algorithm: String(params.algorithm ?? "—"),
      sharpe: params.sharpe != null ? Number(params.sharpe) : null,
      sortino: params.sortino != null ? Number(params.sortino) : null,
      winRate: params.win_rate != null ? Number(params.win_rate) : null,
      nTrades: params.n_trades != null ? Number(params.n_trades) : null,
      turnover: params.turnover != null ? Number(params.turnover) : null,
      totalPnl: params.total_pnl != null ? Number(params.total_pnl) : null,
      meanBrier: params.mean_brier != null ? Number(params.mean_brier) : null,
      maxDrawdownPct: row.max_drawdown_pct,
      params,
    });
  }

  return results;
}

export interface VersionedValidationRow {
  date: string;
  pair: string;
  predicted: string | null;
  confidence: number | null;
  t5Outcome: string;
  t20Outcome: string;
  t5ReturnBps: number | null;
  t20ReturnBps: number | null;
  t5Brier: number | null;
  t20Brier: number | null;
  model_version: string | null;
}

export async function getValidationByVersion(
  supabase: TypedSupabaseClient,
  version: string,
  pair?: string,
  horizon?: "t5" | "t20",
  limit = 100,
): Promise<VersionedValidationRow[]> {
  let q = supabase
    .from("validation_log")
    .select(
      "date,pair,predicted_direction,confidence,t5Outcome:correct_t5,t20Outcome:correct_t20,t5ReturnBps:log_return_t5_bps,t20ReturnBps:log_return_t20_bps,t5Brier:brier_score_t5,t20Brier:brier_score_t20,regime_calls!inner(model_version)",
    )
    .eq("is_superseded", false)
    .eq("regime_calls.model_version", version)
    .order("date", { ascending: false })
    .limit(limit);

  if (pair) q = q.eq("pair", pair);
  if (horizon === "t5") {
    q = q.not("correct_t5", "is", null);
  } else if (horizon === "t20") {
    q = q.not("correct_t20", "is", null);
  }

  const { data, error } = await q;
  if (error || !data) {
    // Fallback: fetch validation_log and filter in-memory if join fails
    const { data: fallback, error: fallbackErr } = await supabase
      .from("validation_log")
      .select("*")
      .eq("is_superseded", false)
      .order("date", { ascending: false })
      .limit(limit);
    if (fallbackErr || !fallback) return [];
    let rows = fallback as ValidationLogRow[];
    if (pair) rows = rows.filter((r) => r.pair === pair);
    return rows.map((r) => ({
      date: r.date,
      pair: r.pair,
      predicted: null,
      confidence: r.confidence,
      t5Outcome: r.correct_t5
        ? "CORRECT"
        : r.correct_t5 === false
          ? "WRONG"
          : "PENDING",
      t20Outcome: r.correct_t20
        ? "CORRECT"
        : r.correct_t20 === false
          ? "WRONG"
          : "PENDING",
      t5ReturnBps: r.log_return_t5_bps,
      t20ReturnBps: r.log_return_t20_bps,
      t5Brier: r.brier_score_t5,
      t20Brier: r.brier_score_t20,
      model_version: null,
    }));
  }

  return (data as unknown as Array<Record<string, unknown>>).map((r) => ({
    date: String(r.date),
    pair: String(r.pair),
    predicted: r.predicted_direction ? String(r.predicted_direction) : null,
    confidence: r.confidence != null ? Number(r.confidence) : null,
    t5Outcome: r.correct_t5
      ? "CORRECT"
      : r.correct_t5 === false
        ? "WRONG"
        : "PENDING",
    t20Outcome: r.correct_t20
      ? "CORRECT"
      : r.correct_t20 === false
        ? "WRONG"
        : "PENDING",
    t5ReturnBps:
      r.log_return_t5_bps != null ? Number(r.log_return_t5_bps) : null,
    t20ReturnBps:
      r.log_return_t20_bps != null ? Number(r.log_return_t20_bps) : null,
    t5Brier: r.brier_score_t5 != null ? Number(r.brier_score_t5) : null,
    t20Brier: r.brier_score_t20 != null ? Number(r.brier_score_t20) : null,
    model_version: version,
  }));
}

export interface VersionedRegimeBreakdownRow {
  pair: string;
  regime: string;
  count: number;
  winRateT5: number | null;
  winRateT20: number | null;
}

export async function getRegimeBreakdownByVersion(
  supabase: TypedSupabaseClient,
  version: string,
  limit = 100,
): Promise<VersionedRegimeBreakdownRow[]> {
  const { data, error } = await supabase
    .from("regime_calls")
    .select("pair,regime")
    .eq("model_version", version)
    .order("date", { ascending: false })
    .limit(limit);

  if (error || !data) return [];

  const counts = new Map<
    string,
    { pair: string; regime: string; count: number }
  >();
  for (const row of data as Array<{ pair: string; regime: string }>) {
    const key = `${row.pair}::${row.regime}`;
    const existing = counts.get(key);
    if (existing) {
      existing.count++;
    } else {
      counts.set(key, { pair: row.pair, regime: row.regime, count: 1 });
    }
  }

  return Array.from(counts.values()).map((c) => ({
    pair: c.pair,
    regime: c.regime,
    count: c.count,
    winRateT5: null,
    winRateT20: null,
  }));
}

/* ─── Site Content (CMS) ──────────────────────────────────────────────── */

export async function getSiteContent(
  supabase: TypedSupabaseClient,
  section?: string,
): Promise<Record<string, string>> {
  const q = supabase
    .from("site_content")
    .select("content_key,content_text")
    .eq("is_active", true);
  if (section) q.eq("section", section);
  const { data, error } = await q;
  if (error || !data) return {};
  return Object.fromEntries(
    (data as SiteContentRow[]).map((r) => [
      r.content_key,
      r.content_text ?? "",
    ]),
  );
}

/* ─── Site Settings (Feature Flags) ───────────────────────────────────── */

export async function getSiteSettings(
  supabase: TypedSupabaseClient,
): Promise<Record<string, string>> {
  const { data, error } = await supabase
    .from("site_settings")
    .select("setting_key,setting_value");
  if (error || !data) return {};
  return Object.fromEntries(
    (data as SiteSettingsRow[]).map((r) => [
      r.setting_key,
      r.setting_value ?? "",
    ]),
  );
}

export async function getSiteSetting(
  supabase: TypedSupabaseClient,
  key: string,
): Promise<string | null> {
  const { data, error } = await supabase
    .from("site_settings")
    .select("setting_value")
    .eq("setting_key", key)
    .maybeSingle();
  if (error || !data) return null;
  return (data as SiteSettingsRow).setting_value;
}
