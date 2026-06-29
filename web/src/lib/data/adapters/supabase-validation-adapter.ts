import type { Database } from "@/lib/supabase/database.types";
import type { RegimeCall } from "../domain/regime";
import type {
  ValidationLogRow as DomainValidationLogRow,
  Horizon,
  RegimeBreakdownEntry,
  ValidationEntry,
  ValidationStats,
} from "../domain/validation";
import {
  formatRegimeLabel,
  toLegacyOutcome,
  toOutcomeLabel,
} from "../presentation/outcomes";
import { formatPairCode } from "../presentation/pairs";

type DbValidationLogRow = Database["public"]["Tables"]["validation_log"]["Row"];
type ValidationStatsRow =
  Database["public"]["Tables"]["validation_stats"]["Row"];
type RegimeCallRow = Database["public"]["Tables"]["regime_calls"]["Row"];

export function toRegimeCall(row: RegimeCallRow): RegimeCall {
  return {
    pair: row.pair,
    date: row.date,
    regime: row.regime,
    confidence: row.confidence,
    signalComposite: row.signal_composite,
    rateSignal: row.rate_signal,
    cotSignal: row.cot_signal,
    volSignal: row.vol_signal,
    rrSignal: row.rr_signal,
    oiSignal: row.oi_signal,
    primaryDriver: row.primary_driver,
    specialSignalValue: row.special_signal_value,
    specialSignalLabel: row.special_signal_label,
    modelVersion: row.model_version,
    dataQualityScore: row.data_quality_score,
    stressLevel: row.stress_level,
    createdAt: row.created_at,
    predictedDirection: row.predicted_direction,
    entryTiming: row.entry_timing,
    positionSize: row.position_size,
    stopLevel: row.stop_level,
  };
}

export function toValidationEntry(
  row: DbValidationLogRow,
  predictedMap: Map<number, string>,
): ValidationEntry {
  return {
    date: row.date,
    pair: formatPairCode(row.pair),
    predicted:
      row.call_id != null ? (predictedMap.get(row.call_id) ?? "—") : "—",
    t5ReturnBps: row.log_return_t5_bps,
    t5ReturnNetBps: row.log_return_net_bps_t5 ?? null,
    t5Outcome: toOutcomeLabel(row.correct_t5, row.actual_direction_t5),
    t5CorrectNet: row.correct_net_t5 ?? null,
    t5CostBps: row.cost_bps_t5 ?? null,
    t5Brier: row.brier_score_t5,
    t20ReturnBps: row.log_return_t20_bps,
    t20ReturnNetBps: row.log_return_net_bps_t20 ?? null,
    t20Outcome: toOutcomeLabel(row.correct_t20, row.actual_direction_t20),
    t20CorrectNet: row.correct_net_t20 ?? null,
    t20CostBps: row.cost_bps_t20 ?? null,
    t20Brier: row.brier_score_t20,
  };
}

export function toValidationLogRow(
  row: DbValidationLogRow & { regime_calls?: { regime: string } | null },
): DomainValidationLogRow {
  return {
    date: row.date,
    pair: formatPairCode(row.pair),
    call: formatRegimeLabel(row.regime_calls?.regime),
    outcome: toLegacyOutcome(row.correct_t5, row.actual_direction_t5),
    returnPct: Number(row.log_return_t5_bps ?? 0),
  };
}

export function toValidationStats(
  row: ValidationStatsRow,
  horizon: Horizon,
): ValidationStats {
  const prefix = horizon === "t5" ? "t5" : "t20";

  return {
    pair: formatPairCode(row.pair),
    horizon,
    winRate: row[`${prefix}_win_rate` as keyof ValidationStatsRow] as
      | number
      | null,
    winRateCI: [
      (row[`${prefix}_win_rate_ci_lower` as keyof ValidationStatsRow] as
        | number
        | null) ?? 0,
      (row[`${prefix}_win_rate_ci_upper` as keyof ValidationStatsRow] as
        | number
        | null) ?? 0,
    ] as [number, number],
    netWinRate:
      (row[`${prefix}_net_win_rate` as keyof ValidationStatsRow] as
        | number
        | null) ?? null,
    netWinRateCI: [
      (row[`${prefix}_net_win_rate_ci_lower` as keyof ValidationStatsRow] as
        | number
        | null) ?? 0,
      (row[`${prefix}_net_win_rate_ci_upper` as keyof ValidationStatsRow] as
        | number
        | null) ?? 0,
    ] as [number, number],
    costBps:
      (row[`${prefix}_cost_bps` as keyof ValidationStatsRow] as
        | number
        | null) ?? null,
    wins: row[`${prefix}_wins` as keyof ValidationStatsRow] as number | null,
    brierScore: row[`${prefix}_mean_brier` as keyof ValidationStatsRow] as
      | number
      | null,
    sampleSize: row[`${prefix}_total_calls` as keyof ValidationStatsRow] as
      | number
      | null,
    avgReturnBps: row[
      `${prefix}_mean_log_return_bps` as keyof ValidationStatsRow
    ] as number | null,
    sharpeLike: row[`${prefix}_sharpe_like` as keyof ValidationStatsRow] as
      | number
      | null,
    rolling90dAccuracy: row[
      `${prefix}_rolling_90d_accuracy` as keyof ValidationStatsRow
    ] as number | null,
    asOfDate: row.as_of_date,
  };
}

export function toRegimeBreakdownEntry(
  row: DbValidationLogRow,
  regime: string,
): RegimeBreakdownEntry {
  return {
    pair: formatPairCode(row.pair),
    regime,
    t5Outcome: toOutcomeLabel(row.correct_t5, row.actual_direction_t5),
    t20Outcome: toOutcomeLabel(row.correct_t20, row.actual_direction_t20),
  };
}

/** Convert domain RegimeCall to legacy queries.ts LatestRegimeCall shape. */
export function toLegacyRegimeCall(call: RegimeCall) {
  return {
    pair: call.pair,
    date: call.date,
    regime: call.regime,
    confidence: call.confidence,
    signal_composite: call.signalComposite,
    rate_signal: call.rateSignal,
    cot_signal: call.cotSignal,
    vol_signal: call.volSignal,
    rr_signal: call.rrSignal,
    oi_signal: call.oiSignal,
    primary_driver: call.primaryDriver,
    special_signal_value: call.specialSignalValue,
    special_signal_label: call.specialSignalLabel,
    model_version: call.modelVersion,
    data_quality_score: call.dataQualityScore,
    stress_level: call.stressLevel,
    created_at: call.createdAt,
    predicted_direction: call.predictedDirection,
    entry_timing: call.entryTiming,
    position_size: call.positionSize,
    stop_level: call.stopLevel,
  };
}

/** Convert domain ValidationEntry to legacy ValidationRowT5 shape (identical). */
export function toLegacyValidationEntry(
  entry: ValidationEntry,
): ValidationEntry {
  return entry;
}
