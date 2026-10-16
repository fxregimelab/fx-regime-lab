export type Horizon = "t5" | "t20";

export type OutcomeLabel = "CORRECT" | "WRONG" | "NEUTRAL" | "—";

export type LegacyOutcome = "correct" | "incorrect" | "neutral";

/** Per-call validation row with T+5 and T+20 horizon metrics (display pair codes). */
export interface ValidationEntry {
  date: string;
  pair: string;
  predicted: string;
  t5ReturnBps: number | null;
  t5ReturnNetBps: number | null;
  t5Outcome: OutcomeLabel;
  t5CorrectNet: boolean | null;
  t5CostBps: number | null;
  t5Brier: number | null;
  t20ReturnBps: number | null;
  t20ReturnNetBps: number | null;
  t20Outcome: OutcomeLabel;
  t20CorrectNet: boolean | null;
  t20CostBps: number | null;
  t20Brier: number | null;
}

/** Legacy validation log row (T+5 only, regime label as call). */
export interface ValidationLogRow {
  date: string;
  pair: string;
  call: string;
  outcome: LegacyOutcome;
  returnPct: number;
}

/** Aggregated validation statistics for a pair and horizon. */
export interface ValidationStats {
  pair: string;
  horizon: Horizon;
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

export interface RegimeBreakdownEntry {
  pair: string;
  regime: string;
  t5Outcome: OutcomeLabel;
  t20Outcome: OutcomeLabel;
}
