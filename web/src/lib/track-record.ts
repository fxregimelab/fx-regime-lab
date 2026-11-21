import type { ValidationRowT5, ValidationStats } from "@/lib/supabase/queries";

export function fmtPctRaw(n: number | null | undefined, digits = 1) {
  if (n == null || !Number.isFinite(n)) return "—";
  const prop = n > 1 ? n / 100 : n;
  const sign = prop >= 0 ? "+" : "";
  return `${sign}${(prop * 100).toFixed(digits)}%`;
}

export function fmtBrier(n: number | null | undefined) {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toFixed(3);
}

export function fmtBps(n: number | null | undefined, digits = 1) {
  if (n == null || !Number.isFinite(n)) return "—";
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(digits)} bps`;
}

function utcToday() {
  return new Date().toISOString().slice(0, 10);
}

function parseUtcDate(value: string) {
  const ymd = value.slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(ymd)) return null;
  const parsed = new Date(`${ymd}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) &&
    parsed.toISOString().slice(0, 10) === ymd
    ? parsed
    : null;
}

function addWeekdays(start: Date, weekdays: number) {
  const result = new Date(start);
  let added = 0;
  while (added < weekdays) {
    result.setUTCDate(result.getUTCDate() + 1);
    const day = result.getUTCDay();
    if (day !== 0 && day !== 6) added++;
  }
  return result;
}

function finiteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

// Includes all persisted calls in the selected population. Missing evaluations
// remain null outcomes; scored share is directional outcomes / all calls.
export function computeStatsFromLog(
  rows: ValidationRowT5[],
  pair: string | null,
  horizon: "t5" | "t20",
  asOfDate = utcToday(),
): ValidationStats {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(asOfDate)) {
    throw new Error(`Invalid as-of date: ${asOfDate}`);
  }
  const asOf = parseUtcDate(asOfDate);
  if (asOf == null) throw new Error(`Invalid as-of date: ${asOfDate}`);
  const outcomeKey = horizon === "t5" ? "t5Outcome" : "t20Outcome";
  const brierKey = horizon === "t5" ? "t5Brier" : "t20Brier";
  const returnKey = horizon === "t5" ? "t5ReturnBps" : "t20ReturnBps";
  const netOutcomeKey = horizon === "t5" ? "t5CorrectNet" : "t20CorrectNet";
  const costKey = horizon === "t5" ? "t5CostBps" : "t20CostBps";
  const netReturnKey = horizon === "t5" ? "t5ReturnNetBps" : "t20ReturnNetBps";
  const horizonDays = horizon === "t5" ? 5 : 20;

  const metadataTuples = new Set(
    rows.map((row) => {
      const withWindow = row as ValidationRowT5 & { windowDays?: number };
      return JSON.stringify([
        row.dataSource?.trim() || "unknown",
        row.strategyVersion?.trim() || "unknown",
        row.modelVersion?.trim() || "unknown",
        row.evaluationVersion?.trim() || "unknown",
        row.populationVersion?.trim() || "unknown",
        Number.isInteger(withWindow.windowDays)
          ? withWindow.windowDays
          : "unknown",
      ]);
    }),
  );
  if (metadataTuples.size > 1) {
    throw new Error("Validation rows contain mixed cohort metadata");
  }
  const metadata = JSON.parse(
    metadataTuples.values().next().value ??
      '["unknown","unknown","unknown","unknown","unknown","unknown"]',
  ) as [string, string, string, string, string, number | "unknown"];

  const cohort = rows.filter((row) => {
    const callDate = parseUtcDate(row.date);
    return (
      (!pair || row.pair === pair) && (callDate == null || callDate <= asOf)
    );
  });

  const mature = cohort.filter((row) => {
    const callDate = parseUtcDate(row.date);
    return callDate != null && addWeekdays(callDate, horizonDays) <= asOf;
  });
  const matureDirectional = mature.filter((row) => {
    const outcome = row[outcomeKey];
    return (
      (row.predicted === "BULLISH" || row.predicted === "BEARISH") &&
      (outcome === "CORRECT" || outcome === "WRONG") &&
      finiteNumber(row[returnKey])
    );
  });

  const wins = matureDirectional.filter(
    (row) => row[outcomeKey] === "CORRECT",
  ).length;
  const directionalCalls = matureDirectional.length;
  const brierValues = matureDirectional
    .map((row) => row[brierKey])
    .filter(
      (value): value is number =>
        finiteNumber(value) && value >= 0 && value <= 1,
    );
  const grossSignedPayoffs = matureDirectional.map((row) => {
    const rawReturn = row[returnKey] as number;
    return row.predicted === "BEARISH" ? -rawReturn : rawReturn;
  });
  const netEligible = matureDirectional.filter(
    (row) =>
      typeof row[netOutcomeKey] === "boolean" &&
      finiteNumber(row[netReturnKey]) &&
      finiteNumber(row[costKey]) &&
      (row[costKey] as number) >= 0,
  );
  const netWins = netEligible.filter(
    (row) => row[netOutcomeKey] === true,
  ).length;
  const costs = netEligible.map((row) => row[costKey] as number);

  const rollingStart = new Date(asOf);
  rollingStart.setUTCDate(rollingStart.getUTCDate() - 89);
  const recentDirectional = matureDirectional.filter((row) => {
    const callDate = parseUtcDate(row.date);
    return callDate != null && callDate >= rollingStart && callDate <= asOf;
  });
  const recentWins = recentDirectional.filter(
    (row) => row[outcomeKey] === "CORRECT",
  ).length;
  const abstainedCalls = mature.filter(
    (row) => row.predicted === "NEUTRAL",
  ).length;
  const unknownDirectionCalls = mature.filter(
    (row) =>
      row.predicted !== "BULLISH" &&
      row.predicted !== "BEARISH" &&
      row.predicted !== "NEUTRAL",
  ).length;
  const missingOutcomeCalls = mature.filter(
    (row) =>
      (row.predicted === "BULLISH" || row.predicted === "BEARISH") &&
      !(
        (row[outcomeKey] === "CORRECT" || row[outcomeKey] === "WRONG") &&
        finiteNumber(row[returnKey])
      ),
  ).length;

  return {
    pair: pair ?? "ALL",
    horizon,
    winRate: directionalCalls > 0 ? wins / directionalCalls : null,
    winRateCI: null,
    netWinRate: netEligible.length > 0 ? netWins / netEligible.length : null,
    netWinRateCI: null,
    costBps:
      costs.length > 0
        ? costs.reduce((sum, value) => sum + value, 0) / costs.length
        : null,
    wins,
    brierScore:
      brierValues.length > 0
        ? brierValues.reduce((sum, value) => sum + value, 0) /
          brierValues.length
        : null,
    sampleSize: directionalCalls,
    totalCalls: cohort.length,
    evaluationCalls: cohort.filter((row) => row.evaluationPresent === true)
      .length,
    missingEvaluationCalls: cohort.filter(
      (row) => row.evaluationPresent !== true,
    ).length,
    matureCalls: mature.length,
    pendingCalls: cohort.length - mature.length,
    unknownDirectionCalls,
    directionalCalls,
    netSampleSize: netEligible.length,
    brierSampleSize: brierValues.length,
    abstainedCalls,
    missingOutcomeCalls,
    coverage: cohort.length > 0 ? directionalCalls / cohort.length : null,
    avgReturnBps:
      grossSignedPayoffs.length > 0
        ? grossSignedPayoffs.reduce((sum, value) => sum + value, 0) /
          grossSignedPayoffs.length
        : null,
    sharpeLike: null,
    rolling90dAccuracy:
      recentDirectional.length > 0
        ? recentWins / recentDirectional.length
        : null,
    asOfDate: asOf.toISOString().slice(0, 10),
    dataSource: metadata[0],
    strategyVersion: metadata[1],
    modelVersion: metadata[2],
    evaluationVersion: metadata[3],
    populationVersion: metadata[4],
    windowDays: metadata[5] === "unknown" ? undefined : metadata[5],
  };
}
