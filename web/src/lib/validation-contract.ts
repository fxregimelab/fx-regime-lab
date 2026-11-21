export const EVALUATION_VERSION = "publication-snapshot-v2";
export const LIVE_MODEL_VERSION = "2.0-live";
export const STRATEGY_VERSION = "v2";

export function validationCohort(dataSource = "live", modelVersion?: string) {
  if (!["live", "backtest", "unknown"].includes(dataSource)) {
    throw new Error("Unsupported validation data source");
  }
  const model =
    modelVersion ?? (dataSource === "live" ? LIVE_MODEL_VERSION : null);
  if (!model?.trim()) throw new Error("An explicit model version is required");
  return {
    dataSource,
    strategyVersion: STRATEGY_VERSION,
    modelVersion: model,
    evaluationVersion: EVALUATION_VERSION,
    windowDays: 0,
    populationVersion: "published-calls-v1",
  };
}

export function validationOutcome(
  predicted: string | null,
  rawReturn: number | null,
  correct: boolean | null,
): "CORRECT" | "WRONG" | "NEUTRAL" | "—" {
  if (rawReturn == null || !Number.isFinite(rawReturn)) return "—";
  if (predicted === "NEUTRAL") return "NEUTRAL";
  if (predicted !== "BULLISH" && predicted !== "BEARISH") return "—";
  if (correct === true) return "CORRECT";
  if (correct === false) return "WRONG";
  return "—";
}
