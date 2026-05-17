export type RegimeType = "Risk-On" | "Risk-Off" | "Transitional";

/** Heuristic classification of regime names into Risk-On / Risk-Off / Transitional.
 *  Based on directional bias implied by the regime label.
 */
export function classifyRegime(regime: string): RegimeType {
  const u = regime.toUpperCase();

  // Risk-On: base currency strengthening, directional upward
  if (
    u.includes("STRENGTH") ||
    u.includes("APPRECIATION") ||
    u === "TRENDING" ||
    u === "BREAKOUT" ||
    u === "ACCUMULATION"
  ) {
    return "Risk-On";
  }

  // Risk-Off: base currency weakening, directional downward
  if (
    u.includes("WEAKNESS") ||
    u.includes("DEPRECIATION") ||
    u === "REVERSAL" ||
    u === "DISTRIBUTION"
  ) {
    return "Risk-Off";
  }

  // Transitional: everything else
  return "Transitional";
}
