import { DEFAULT_ACCURACY_GATE, EURUSD_ACCURACY_GATE } from "@/lib/config";
import { validationCohort, validationOutcome } from "../validation-contract";
import type { Database, Json } from "./database.types";

type RegimeCallRow = Database["public"]["Tables"]["regime_calls"]["Row"];
type SignalRow = Database["public"]["Tables"]["signals"]["Row"];
type LivePublicationSignalRow =
  Database["public"]["Views"]["live_publication_signals"]["Row"];
type ValidationObservationRow =
  Database["public"]["Views"]["validation_observations"]["Row"];
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
  id: number;
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
  structural_instability: boolean | null;
  ecb_balance_sheet: number | null;
  bund_btp_spread: number | null;
  boj_policy_rate: number | null;
  created_at: string | null;
}

export interface ValidationRow {
  date: string;
  pair: string;
  call: string;
  outcome: "correct" | "incorrect" | "neutral" | "pending";
  return_pct: number | null;
}

export interface ValidationStats {
  totalCalls?: number;
  evaluationCalls?: number;
  missingEvaluationCalls?: number;
  populationVersion?: string;
  matureCalls?: number;
  pendingCalls?: number;
  unknownDirectionCalls?: number;
  directionalCalls?: number;
  brierSampleSize?: number;
  abstainedCalls?: number;
  missingOutcomeCalls?: number;
  coverage?: number | null;
  dataSource?: string;
  strategyVersion?: string;
  modelVersion?: string;
  evaluationVersion?: string;
  windowDays?: number;

  pair: string;
  horizon: "t5" | "t20";
  winRate: number | null;
  winRateCI: [number, number] | null;
  netWinRate: number | null;
  netWinRateCI: [number, number] | null;
  costBps: number | null;
  wins: number | null;
  brierScore: number | null;
  sampleSize: number | null;
  netSampleSize?: number | null;
  avgReturnBps: number | null;
  sharpeLike: number | null;
  rolling90dAccuracy: number | null;
  asOfDate: string;
}

export interface ValidationRowT5 {
  callId?: number;
  evaluationId?: number | null;
  evaluationPresent?: boolean;
  populationVersion?: string;
  dataSource?: string;
  strategyVersion?: string;
  modelVersion?: string;
  evaluationVersion?: string;
  regime?: string;
  date: string;
  pair: string;
  predicted: string;
  t5ReturnBps: number | null;
  t5ReturnNetBps: number | null;
  t5Outcome: "CORRECT" | "WRONG" | "NEUTRAL" | "—";
  t5CorrectNet: boolean | null;
  t5CostBps: number | null;
  t5Brier: number | null;
  t20ReturnBps: number | null;
  t20ReturnNetBps: number | null;
  t20Outcome: "CORRECT" | "WRONG" | "NEUTRAL" | "—";
  t20CorrectNet: boolean | null;
  t20CostBps: number | null;
  t20Brier: number | null;
}

function toLatestRegimeCall(row: RegimeCallRow): LatestRegimeCall {
  return {
    id: row.id,
    pair: row.pair,
    date: row.date,
    regime: row.regime,
    confidence: row.confidence,
    signal_composite: row.signal_composite,
    rate_signal: row.rate_signal,
    cot_signal: row.cot_signal,
    vol_signal: row.vol_signal,
    rr_signal: row.rr_signal,
    oi_signal: row.oi_signal,
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
    spot: row.spot ?? null,
    rate_diff_2y: row.rate_diff_2y ?? null,
    cot_percentile: row.cot_percentile ?? null,
    realized_vol_20d: row.realized_vol_20d ?? null,
    realized_vol_5d: row.realized_vol_5d ?? null,
    implied_vol_30d: row.implied_vol_30d ?? null,
    day_change: row.day_change ?? null,
    day_change_pct: row.day_change_pct ?? null,
    cross_asset_us10y: row.cross_asset_us10y ?? null,
    realized_vol_rank: row.realized_vol_rank ?? null,
    rate_z_tactical: row.rate_z_tactical ?? null,
    rate_z_structural: row.rate_z_structural ?? null,
    z_blended: row.z_blended ?? null,
    rate_diff_10y_real: row.rate_diff_10y_real ?? null,
    breakeven_inflation_10y: row.breakeven_inflation_10y ?? null,
    skew_alignment: row.skew_alignment ?? null,
    risk_reversal_25d: row.risk_reversal_25d ?? null,
    fpi_flow: row.fpi_flow ?? null,
    cot_net_pos: row.cot_net_pos ?? null,
    cot_asset_mgr_net: row.cot_asset_mgr_net ?? null,
    cot_lev_money_net: row.cot_lev_money_net ?? null,
    india_vix: row.india_vix ?? null,
    inr_forward_premium: row.inr_forward_premium ?? null,
    oi_delta: row.oi_delta ?? null,
    volume_rvol: row.volume_rvol ?? null,
    structural_instability:
      typeof row.structural_instability === "boolean"
        ? row.structural_instability
        : null,
    ecb_balance_sheet: row.ecb_balance_sheet ?? null,
    bund_btp_spread: row.bund_btp_spread ?? null,
    boj_policy_rate: row.boj_policy_rate ?? null,
    created_at: null,
  };
}

import type { createClient } from "./server";

type TypedSupabaseClient = Awaited<ReturnType<typeof createClient>>;

const LIVE_PUBLICATION_PAIRS = ["EURUSD", "USDJPY", "USDINR"] as const;
const PUBLICATION_PAGE_SIZE = 1000;

function todayUtc(): string {
  return new Date().toISOString().slice(0, 10);
}

function signalPayloadRow(row: LivePublicationSignalRow): SignalRow {
  const payload = row.signal_payload;
  if (!payload || Array.isArray(payload) || typeof payload !== "object")
    throw new Error(`Publication signal evidence ${row.call_id} is malformed`);
  const object = payload as Record<string, Json | undefined>;
  if (object.pair !== row.pair || object.date !== row.date)
    throw new Error(
      `Publication signal evidence ${row.call_id} has inconsistent identity`,
    );
  return object as SignalRow;
}

export async function getLatestRegimeCalls(
  supabase: TypedSupabaseClient,
  cutoff = todayUtc(),
): Promise<Record<string, LatestRegimeCall>> {
  const latest: Record<string, LatestRegimeCall> = {};
  const rows = await Promise.all(
    LIVE_PUBLICATION_PAIRS.map(async (pair) => {
      const { data, error } = await supabase
        .from("regime_calls")
        .select("*")
        .eq("pair", pair)
        .eq("data_source", "live")
        .eq("strategy_version", "v2")
        .lte("date", cutoff)
        .order("date", { ascending: false })
        .order("id", { ascending: false })
        .limit(1);
      if (error)
        throw new Error(`Current publications unavailable: ${error.message}`);
      if (!data) throw new Error("Current publications returned no response");
      return (data as RegimeCallRow[])[0] ?? null;
    }),
  );
  for (const row of rows) {
    if (row) latest[row.pair] = toLatestRegimeCall(row);
  }
  return latest;
}

export async function getLatestSignals(
  supabase: TypedSupabaseClient,
  calls: Record<string, LatestRegimeCall>,
): Promise<Record<string, LatestSignal>> {
  const callIds = Object.values(calls).map((call) => call.id);
  if (callIds.length === 0) return {};
  const { data, error } = await supabase
    .from("live_publication_signals")
    .select("call_id,pair,date,signal_payload")
    .in("call_id", callIds);

  if (error)
    throw new Error(
      `Publication signal evidence unavailable: ${error.message}`,
    );
  if (!data)
    throw new Error("Publication signal evidence returned no response");

  const latest: Record<string, LatestSignal> = {};
  for (const row of data as LivePublicationSignalRow[]) {
    const selected = calls[row.pair];
    if (!selected || selected.id !== row.call_id) continue;
    if (selected.date !== row.date)
      throw new Error(
        `Publication signal evidence ${row.call_id} does not match its selected call`,
      );
    const payload = signalPayloadRow(row);
    latest[row.pair] = toLatestSignal(payload);
  }
  return latest;
}

export async function getValidationLog(
  supabase: TypedSupabaseClient,
  limit = 20,
): Promise<ValidationRow[]> {
  return (await getValidationLogT5T20(supabase, limit)).map((r) => ({
    date: r.date,
    pair: r.pair,
    call: r.predicted,
    outcome:
      r.t5Outcome === "CORRECT"
        ? "correct"
        : r.t5Outcome === "WRONG"
          ? "incorrect"
          : r.t5Outcome === "NEUTRAL"
            ? "neutral"
            : "pending",
    return_pct: r.t5ReturnBps,
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

const PAIR_LABELS: Record<string, string> = {
  EURUSD: "EUR/USD",
  USDJPY: "USD/JPY",
  USDINR: "USD/INR",
};

async function fetchValidationCohort(
  supabase: TypedSupabaseClient,
  table: "validation_observations" | "validation_stats",
  limit: number | null,
  dataSource: string,
  modelVersion?: string,
  pair?: string,
): Promise<(ValidationObservationRow | ValidationStatsRow)[]> {
  const cohort = validationCohort(dataSource, modelVersion);
  if (limit !== null && (!Number.isInteger(limit) || limit < 0))
    throw new Error("Invalid validation row limit");
  const rows: (ValidationObservationRow | ValidationStatsRow)[] = [];
  while (limit === null || rows.length < limit) {
    const size = limit === null ? 1000 : Math.min(1000, limit - rows.length);
    let q = supabase
      .from(table)
      .select("*")
      .eq("data_source", cohort.dataSource)
      .eq("strategy_version", cohort.strategyVersion)
      .eq("model_version", cohort.modelVersion)
      .eq("evaluation_version", cohort.evaluationVersion)
      .order(table === "validation_observations" ? "date" : "as_of_date", {
        ascending: false,
      })
      .order("id", { ascending: false });
    q = q.eq("population_version", cohort.populationVersion);
    if (table === "validation_stats")
      q = q.eq("window_days", cohort.windowDays);
    if (pair) q = q.eq("pair", pair);
    const { data, error } = await q.range(rows.length, rows.length + size - 1);
    if (error)
      throw new Error(`Validation evidence unavailable: ${error.message}`);
    if (!data) throw new Error("Validation evidence returned no response");
    const page = data as (ValidationObservationRow | ValidationStatsRow)[];
    rows.push(...page);
    if (page.length < size) break;
  }
  return rows;
}

function toValidationRow(r: ValidationObservationRow): ValidationRowT5 {
  return {
    callId: r.call_id,
    evaluationId: r.evaluation_id,
    evaluationPresent: r.evaluation_present,
    populationVersion: r.population_version,
    date: r.call_date ?? r.date,
    pair: PAIR_LABELS[r.pair] ?? r.pair,
    predicted: r.predicted_direction ?? "—",
    regime: r.predicted_regime ?? "UNKNOWN",
    dataSource: r.data_source ?? "unknown",
    strategyVersion: r.strategy_version ?? "unknown",
    modelVersion: r.model_version ?? "unknown",
    evaluationVersion: r.evaluation_version,
    t5ReturnBps: r.log_return_t5_bps,
    t5ReturnNetBps: r.log_return_net_bps_t5,
    t5Outcome: validationOutcome(
      r.predicted_direction,
      r.log_return_t5_bps,
      r.correct_t5,
    ),
    t5CorrectNet: r.correct_net_t5,
    t5CostBps: r.cost_bps_t5,
    t5Brier: r.brier_score_t5,
    t20ReturnBps: r.log_return_t20_bps,
    t20ReturnNetBps: r.log_return_net_bps_t20,
    t20Outcome: validationOutcome(
      r.predicted_direction,
      r.log_return_t20_bps,
      r.correct_t20,
    ),
    t20CorrectNet: r.correct_net_t20,
    t20CostBps: r.cost_bps_t20,
    t20Brier: r.brier_score_t20,
  };
}

export async function getValidationStats(
  supabase: TypedSupabaseClient,
  horizon: "t5" | "t20",
  dataSource = "live",
  modelVersion?: string,
): Promise<ValidationStats[]> {
  const rows = (await fetchValidationCohort(
    supabase,
    "validation_stats",
    null,
    dataSource,
    modelVersion,
  )) as ValidationStatsRow[];
  const seen = new Set<string>();
  return rows
    .filter((r) => {
      if (seen.has(r.pair)) return false;
      seen.add(r.pair);
      return true;
    })
    .map((r) => {
      const number = (suffix: string): number | null => {
        const value = r[`${horizon}_${suffix}` as keyof ValidationStatsRow];
        return typeof value === "number" && Number.isFinite(value)
          ? value
          : null;
      };
      const interval = (prefix: string): [number, number] | null => {
        const low = number(`${prefix}_ci_lower`);
        const high = number(`${prefix}_ci_upper`);
        return low !== null && high !== null ? [low, high] : null;
      };
      const directional = number("directional_calls") ?? 0;
      const total = number("total_calls") ?? 0;
      return {
        pair: PAIR_LABELS[r.pair] ?? r.pair,
        horizon,
        winRate: number("win_rate"),
        winRateCI: interval("win_rate"),
        netWinRate: number("net_win_rate"),
        netWinRateCI: interval("net_win_rate"),
        costBps: number("cost_bps"),
        wins: number("wins"),
        brierScore: number("mean_brier"),
        sampleSize: directional,
        directionalCalls: directional,
        totalCalls: total,
        evaluationCalls: number("evaluation_calls") ?? 0,
        missingEvaluationCalls: number("missing_evaluation_calls") ?? 0,
        populationVersion: r.population_version,
        matureCalls: number("mature_calls") ?? 0,
        pendingCalls: number("pending_calls") ?? 0,
        unknownDirectionCalls: number("unknown_direction_calls") ?? 0,
        netSampleSize: number("net_directional_calls"),
        brierSampleSize: number("probability_score_calls") ?? 0,
        abstainedCalls: number("abstention_calls") ?? 0,
        missingOutcomeCalls: number("missing_outcome_calls") ?? 0,
        coverage: total > 0 ? directional / total : null,
        avgReturnBps: number("mean_signed_gross_return_bps"),
        sharpeLike: null,
        rolling90dAccuracy: number("rolling_90d_accuracy"),
        asOfDate: r.as_of_date,
        dataSource: r.data_source ?? "unknown",
        strategyVersion: r.strategy_version,
        modelVersion: r.model_version,
        evaluationVersion: r.evaluation_version,
        windowDays: r.window_days,
      };
    });
}

export async function getValidationLogT5T20(
  supabase: TypedSupabaseClient,
  limit: number | null = 100,
  dataSource = "live",
  modelVersion?: string,
): Promise<ValidationRowT5[]> {
  const rows = await fetchValidationCohort(
    supabase,
    "validation_observations",
    limit,
    dataSource,
    modelVersion,
  );
  return (rows as ValidationObservationRow[]).map(toValidationRow);
}

export interface RegimeBreakdownRow {
  pair: string;
  regime: string;
  t5Outcome: "CORRECT" | "WRONG" | "NEUTRAL" | "—";
  t20Outcome: "CORRECT" | "WRONG" | "NEUTRAL" | "—";
}

export async function getRegimeBreakdown(
  supabase: TypedSupabaseClient,
  limit: number | null = 100,
  dataSource = "live",
  modelVersion?: string,
): Promise<RegimeBreakdownRow[]> {
  return (
    await getValidationLogT5T20(supabase, limit, dataSource, modelVersion)
  ).map((r) => ({
    pair: r.pair,
    regime: r.regime ?? "UNKNOWN",
    t5Outcome: r.t5Outcome,
    t20Outcome: r.t20Outcome,
  }));
}

export async function getValidationLogForPair(
  supabase: TypedSupabaseClient,
  pair: string,
  limit: number | null = 200,
): Promise<ValidationRowT5[]> {
  const code = pair.replaceAll("/", "");
  return (
    (await fetchValidationCohort(
      supabase,
      "validation_observations",
      limit,
      "live",
      undefined,
      code,
    )) as ValidationObservationRow[]
  ).map(toValidationRow);
}

export async function getHistoricalRegimeCalls(
  supabase: TypedSupabaseClient,
  pair: string,
  limit = 30,
) {
  if (!Number.isInteger(limit) || limit < 0)
    throw new Error("Invalid publication history limit");
  if (limit === 0) return [];
  const pairCode = pair.replaceAll("/", "");
  if (!(LIVE_PUBLICATION_PAIRS as readonly string[]).includes(pairCode))
    throw new Error(`Unsupported publication pair: ${pair}`);
  type HistoryRow = {
    id: number;
    date: string;
    regime: string;
    confidence: number | null;
    signal_composite: number | null;
    primary_driver: string | null;
    rate_signal: string | null;
    entry_timing: string | null;
    position_size: string | null;
    stop_level: number | null;
    created_at: string | null;
    predicted_direction: string | null;
    model_version: string | null;
  };
  const history: HistoryRow[] = [];
  const seenDates = new Set<string>();
  let offset = 0;
  while (history.length < limit) {
    const { data, error } = await supabase
      .from("regime_calls")
      .select(
        "id,date,regime,confidence,signal_composite,primary_driver,rate_signal,entry_timing,position_size,stop_level,created_at,predicted_direction,model_version",
      )
      .eq("pair", pairCode)
      .eq("data_source", "live")
      .eq("strategy_version", "v2")
      .lte("date", todayUtc())
      .order("date", { ascending: false })
      .order("id", { ascending: false })
      .range(offset, offset + PUBLICATION_PAGE_SIZE - 1);
    if (error)
      throw new Error(`Publication history unavailable: ${error.message}`);
    if (!data) throw new Error("Publication history returned no response");
    for (const row of data as HistoryRow[]) {
      if (seenDates.has(row.date)) continue;
      seenDates.add(row.date);
      history.push(row);
      if (history.length === limit) break;
    }
    if (data.length < PUBLICATION_PAGE_SIZE) break;
    offset += data.length;
  }
  return history;
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
  const [t5, t20] = await Promise.all([
    getValidationStats(supabase, "t5"),
    getValidationStats(supabase, "t20"),
  ]);
  const label = PAIR_LABELS[pair] ?? pair;
  const a = t5.find((r) => r.pair === label);
  const b = t20.find((r) => r.pair === label);
  if (!a && !b) return null;
  return {
    t5WinRate: a?.winRate ?? null,
    t5Brier: a?.brierScore ?? null,
    t5SampleSize: a?.sampleSize ?? null,
    t5SharpeLike: null,
    t20WinRate: b?.winRate ?? null,
    t20Brier: b?.brierScore ?? null,
    t20SampleSize: b?.sampleSize ?? null,
    t20SharpeLike: null,
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
  return (await getValidationLogForPair(supabase, pair, limit)).map((r) => ({
    date: r.date,
    predicted: r.predicted,
    t5Outcome: r.t5Outcome,
    t5ReturnBps: r.t5ReturnBps,
    t5Brier: r.t5Brier,
    t20Outcome: r.t20Outcome,
    t20ReturnBps: r.t20ReturnBps,
    t20Brier: r.t20Brier,
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
  const stats = await getValidationStats(supabase, "t5");
  return stats.flatMap((row) => {
    if (row.pair === "ALL" || row.rolling90dAccuracy == null) return [];
    const pair = row.pair.replaceAll("/", "");
    const gate =
      pair === "EURUSD" ? EURUSD_ACCURACY_GATE : DEFAULT_ACCURACY_GATE;
    return row.rolling90dAccuracy < gate
      ? [
          {
            pair,
            accuracy: row.rolling90dAccuracy,
            threshold: gate,
            severity:
              row.rolling90dAccuracy < DEFAULT_ACCURACY_GATE
                ? ("critical" as const)
                : ("warning" as const),
          },
        ]
      : [];
  });
}

/* ─── Backtest / Versioned Queries ─────────────────────────────────────── */

export async function getBacktestVersions(
  supabase: TypedSupabaseClient,
): Promise<string[]> {
  const versions = new Set<string>();
  let offset = 0;
  while (true) {
    const { data, error } = await supabase
      .from("regime_calls")
      .select("id,model_version")
      .eq("data_source", "backtest")
      .eq("strategy_version", "v2")
      .order("id")
      .range(offset, offset + 999);
    if (error)
      throw new Error(`Backtest versions unavailable: ${error.message}`);
    if (!data) throw new Error("Backtest versions returned no response");
    for (const row of data as Pick<RegimeCallRow, "id" | "model_version">[])
      if (row.model_version?.trim()) versions.add(row.model_version);
    if (data.length < 1000) break;
    offset += data.length;
  }
  return [...versions].sort().reverse();
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
    .eq("data_source", "backtest")
    .eq("strategy_version", "v2")
    .order("date", { ascending: false })
    .limit(limit);

  if (pair) q = q.eq("pair", pair);
  if (dateRange) {
    q = q.gte("date", dateRange.from).lte("date", dateRange.to);
  }

  const { data, error } = await q;
  if (error) throw new Error(`Versioned calls unavailable: ${error.message}`);
  if (!data) return [];
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
  const raw = (await fetchValidationCohort(
    supabase,
    "validation_observations",
    null,
    "backtest",
    version,
    pair,
  )) as ValidationObservationRow[];
  return raw
    .map((r) => ({
      ...toValidationRow(r),
      confidence: r.confidence,
      model_version: r.model_version,
    }))
    .filter(
      (r) =>
        !horizon ||
        (horizon === "t5"
          ? ["CORRECT", "WRONG"].includes(r.t5Outcome)
          : ["CORRECT", "WRONG"].includes(r.t20Outcome)),
    )
    .slice(0, limit);
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
  _limit = 100,
): Promise<VersionedRegimeBreakdownRow[]> {
  const rows = await getRegimeBreakdown(supabase, null, "backtest", version);
  const groups = new Map<string, RegimeBreakdownRow[]>();
  for (const row of rows) {
    const key = `${row.pair}::${row.regime}`;
    groups.set(key, [...(groups.get(key) ?? []), row]);
  }
  return [...groups.values()].map((group) => {
    const accuracy = (h: "t5Outcome" | "t20Outcome") => {
      const eligible = group.filter(
        (r) => r[h] === "CORRECT" || r[h] === "WRONG",
      );
      return eligible.length
        ? eligible.filter((r) => r[h] === "CORRECT").length / eligible.length
        : null;
    };
    return {
      pair: group[0].pair,
      regime: group[0].regime,
      count: group.length,
      winRateT5: accuracy("t5Outcome"),
      winRateT20: accuracy("t20Outcome"),
    };
  });
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
