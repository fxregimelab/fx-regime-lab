import type { LegacyOutcome, OutcomeLabel } from "../domain/validation";

/** Map gross correctness + realized direction to display outcome label. */
export function toOutcomeLabel(
  correct: boolean | null | undefined,
  actualDirection: string | null | undefined,
): OutcomeLabel {
  if (correct) return "CORRECT";
  if (actualDirection === "NEUTRAL") return "NEUTRAL";
  if (actualDirection != null) return "WRONG";
  return "—";
}

/** Map gross correctness + realized direction to legacy outcome string. */
export function toLegacyOutcome(
  correct: boolean | null | undefined,
  actualDirection: string | null | undefined,
): LegacyOutcome {
  if (correct) return "correct";
  if (actualDirection === "NEUTRAL") return "neutral";
  return "incorrect";
}

/** Format regime enum for display (RISK_ON → RISK ON). */
export function formatRegimeLabel(regime: string | null | undefined): string {
  if (!regime) return "—";
  return regime.replace(/_/g, " ");
}
