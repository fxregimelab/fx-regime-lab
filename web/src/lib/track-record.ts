import type { ValidationRowT5, ValidationStats } from "@/lib/supabase/queries";

export function fmtPctRaw(n: number | null | undefined, digits = 1) {
  if (n == null) return "—";
  const prop = n > 1 ? n / 100 : n;
  const sign = prop >= 0 ? "+" : "";
  return `${sign}${(prop * 100).toFixed(digits)}%`;
}

export function fmtBrier(n: number | null | undefined) {
  if (n == null) return "—";
  return n.toFixed(3);
}

export function fmtBps(n: number | null | undefined, digits = 1) {
  if (n == null) return "—";
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(digits)} bps`;
}

export function computeStatsFromLog(
  rows: ValidationRowT5[],
  pair: string | null,
  horizon: "t5" | "t20",
): ValidationStats {
  const filtered = pair ? rows.filter((r) => r.pair === pair) : rows;
  const outcomeKey = horizon === "t5" ? "t5Outcome" : "t20Outcome";
  const brierKey = horizon === "t5" ? "t5Brier" : "t20Brier";
  const returnKey = horizon === "t5" ? "t5ReturnBps" : "t20ReturnBps";

  const valid = filtered.filter(
    (r) =>
      r[outcomeKey as keyof ValidationRowT5] === "CORRECT" ||
      r[outcomeKey as keyof ValidationRowT5] === "WRONG",
  );
  const wins = valid.filter(
    (r) => r[outcomeKey as keyof ValidationRowT5] === "CORRECT",
  ).length;
  const sampleSize = valid.length;
  const winRate = sampleSize > 0 ? wins / sampleSize : null;

  const brierValues = filtered
    .map((r) => r[brierKey as keyof ValidationRowT5] as number | null)
    .filter((v): v is number => v != null);
  const brierScore =
    brierValues.length > 0
      ? brierValues.reduce((s, v) => s + v, 0) / brierValues.length
      : null;

  const returns = filtered
    .map((r) => r[returnKey as keyof ValidationRowT5] as number | null)
    .filter((v): v is number => v != null);
  const avgReturnBps =
    returns.length > 0
      ? returns.reduce((s, v) => s + v, 0) / returns.length
      : null;

  let sharpeLike: number | null = null;
  if (avgReturnBps != null && returns.length > 1) {
    const mean = avgReturnBps;
    const variance =
      returns.reduce((s, v) => s + (v - mean) ** 2, 0) / (returns.length - 1);
    sharpeLike = variance > 0 ? mean / Math.sqrt(variance) : null;
  }

  const netOutcomeKey = horizon === "t5" ? "t5CorrectNet" : "t20CorrectNet";
  const costKey = horizon === "t5" ? "t5CostBps" : "t20CostBps";
  const netReturnKey = horizon === "t5" ? "t5ReturnNetBps" : "t20ReturnNetBps";

  const netValid = valid.filter(
    (r) =>
      r[netOutcomeKey as keyof ValidationRowT5] === true ||
      r[netOutcomeKey as keyof ValidationRowT5] === false,
  );
  const netWins = netValid.filter(
    (r) => r[netOutcomeKey as keyof ValidationRowT5] === true,
  ).length;
  const netWinRate = netValid.length > 0 ? netWins / netValid.length : null;

  const costs = netValid
    .map((r) => r[costKey as keyof ValidationRowT5] as number | null)
    .filter((v): v is number => v != null);
  const avgCostBps =
    netValid.length > 0 && costs.length > 0
      ? Number.parseFloat(
          (costs.reduce((s, v) => s + v, 0) / costs.length).toFixed(2),
        )
      : null;

  const netReturns = filtered
    .map((r) => r[netReturnKey as keyof ValidationRowT5] as number | null)
    .filter((v): v is number => v != null);
  const avgNetReturnBps =
    netReturns.length > 0
      ? netReturns.reduce((s, v) => s + v, 0) / netReturns.length
      : null;

  const sortedDates = [...filtered.map((r) => r.date)].sort();
  const latestDate =
    sortedDates.length > 0 ? sortedDates[sortedDates.length - 1] : "";
  const cutoff90d = new Date(latestDate || Date.now());
  cutoff90d.setDate(cutoff90d.getDate() - 90);
  const cutoffStr = cutoff90d.toISOString().split("T")[0];
  const recent90 = valid.filter((r) => r.date >= cutoffStr);
  const rolling90dAccuracy =
    recent90.length > 0
      ? recent90.filter(
          (r) => r[outcomeKey as keyof ValidationRowT5] === "CORRECT",
        ).length / recent90.length
      : null;

  return {
    pair: pair ?? "ALL",
    horizon,
    winRate,
    winRateCI: null,
    netWinRate,
    netWinRateCI: null,
    costBps: avgCostBps,
    wins,
    brierScore,
    sampleSize,
    netSampleSize: netValid.length > 0 ? netValid.length : null,
    avgReturnBps: avgNetReturnBps ?? avgReturnBps,
    sharpeLike,
    rolling90dAccuracy,
    asOfDate: latestDate,
  };
}
