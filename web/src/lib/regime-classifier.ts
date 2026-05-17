export type RegimeType = "Risk-On" | "Risk-Off" | "Transitional";

/** Heuristic classification of regime names into Risk-On / Risk-Off / Transitional.
 *  Based on directional bias implied by the regime label.
 *
 *  Pair-aware rules resolve ambiguity for regimes like RISK_ON_DOLLAR_OFF
 *  where the directional impact depends on whether USD is the base or quote.
 */
export function classifyRegime(regime: string, pair?: string): RegimeType {
  const u = regime.toUpperCase();
  const pairU = pair?.toUpperCase() ?? "";
  const isUsdBase = pairU.startsWith("USD");
  const isUsdInr = pairU === "USD/INR";

  // ── Pair-aware USD strength/weakness overrides ──────────────────────────
  // DOLLAR_ON  → USD strong → Risk-On for USD-base pairs, Risk-Off for others
  // DOLLAR_OFF → USD weak  → Risk-Off for USD-base pairs, Risk-On for others
  if (u.includes("DOLLAR_ON")) {
    return isUsdBase ? "Risk-On" : "Risk-Off";
  }
  if (u.includes("DOLLAR_OFF")) {
    return isUsdBase ? "Risk-Off" : "Risk-On";
  }

  // INR appreciation/depreciation only directly affects USD/INR
  if (u.includes("INR_APPRECIATION")) {
    return isUsdInr ? "Risk-Off" : "Transitional";
  }
  if (u.includes("INR_DEPRECIATION")) {
    return isUsdInr ? "Risk-On" : "Transitional";
  }

  // ── Generic substring classification (pair-agnostic) ────────────────────
  // Risk-On: base currency strengthening, directional upward
  if (
    u.includes("STRENGTH") ||
    u.includes("APPRECIATION") ||
    u.includes("RISK_ON") ||
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
    u.includes("RISK_OFF") ||
    u === "REVERSAL" ||
    u === "DISTRIBUTION"
  ) {
    return "Risk-Off";
  }

  // Transitional: everything else
  return "Transitional";
}
