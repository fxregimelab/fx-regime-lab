/**
 * FX Regime Lab — Pair Profiles
 *
 * Pair-specific methodology configuration derived from the Council of Markets
 * (Round 10). Each pair is a different asset class with its own:
 * - Signal weights (rate, COT, vol, OI, special)
 * - Special signal construction
 * - Driver tag for UI display
 * - Confidence adjustment rules
 * - Regime threshold calibration
 *
 * Source of truth: Supabase `pair_profiles` table (for backend pipeline).
 * This file is the frontend mirror for display/rendering purposes.
 */

export interface PairProfile {
  pair: string;
  display: string;
  urlSlug: string;
  pairColor: string;
  rateWeight: number;
  cotWeight: number;
  volWeight: number;
  oiWeight: number;
  specialWeight: number;
  specialSignalLabel: string;
  specialSignalSource: string;
  driverTag: string;
  primaryAnchorMarket: string;
  regimeThresholds: {
    strongUsdStrength: number;
    moderateUsdStrength: number;
    neutralUpper: number;
    neutralLower: number;
    moderateUsdWeakness: number;
    strongUsdWeakness: number;
  };
  confidenceAdjustment: {
    type: "none" | "additive" | "subtractive";
    condition: string;
    value: number;
    rationale: string;
  };
}

export const PAIR_PROFILES: Record<string, PairProfile> = {
  EURUSD: {
    pair: "EURUSD",
    display: "EUR/USD",
    urlSlug: "eurusd",
    pairColor: "#4BA3E3",
    rateWeight: 0.4,
    cotWeight: 0.25,
    volWeight: 0.2,
    oiWeight: 0.1,
    specialWeight: 0.05,
    specialSignalLabel: "ECB_sentiment",
    specialSignalSource: "NLP on ECB speeches",
    driverTag: "Rates-driven",
    primaryAnchorMarket: "London",
    regimeThresholds: {
      strongUsdStrength: 1.2,
      moderateUsdStrength: 0.6,
      neutralUpper: 0.4,
      neutralLower: -0.4,
      moderateUsdWeakness: -0.6,
      strongUsdWeakness: -1.2,
    },
    confidenceAdjustment: {
      type: "none",
      condition: "always",
      value: 0,
      rationale: "Baseline — well-behaved rates cross",
    },
  },

  USDJPY: {
    pair: "USDJPY",
    display: "USD/JPY",
    urlSlug: "usdjpy",
    pairColor: "#F5923A",
    rateWeight: 0.3,
    cotWeight: 0.2,
    volWeight: 0.25,
    oiWeight: 0.15,
    specialWeight: 0.1,
    specialSignalLabel: "JPY_funding_stress",
    specialSignalSource: "USD/JPY 3M cross-currency basis",
    driverTag: "Funding-driven",
    primaryAnchorMarket: "Tokyo",
    regimeThresholds: {
      strongUsdStrength: 1.2,
      moderateUsdStrength: 0.6,
      neutralUpper: 0.4,
      neutralLower: -0.4,
      moderateUsdWeakness: -0.6,
      strongUsdWeakness: -1.2,
    },
    confidenceAdjustment: {
      type: "additive",
      condition: "S_JPY > 0.5",
      value: 0.05,
      rationale: "Funding stress adds conviction",
    },
  },

  USDINR: {
    pair: "USDINR",
    display: "USD/INR",
    urlSlug: "usdinr",
    pairColor: "#FB923C",
    rateWeight: 0.3,
    cotWeight: 0.1,
    volWeight: 0.2,
    oiWeight: 0.1,
    specialWeight: 0.3,
    specialSignalLabel: "EM_carry_RBI",
    specialSignalSource: "Brent + RBI forward book + EM carry index",
    driverTag: "Carry-sensitive",
    primaryAnchorMarket: "Mumbai",
    regimeThresholds: {
      strongUsdStrength: 1.2,
      moderateUsdStrength: 0.6,
      neutralUpper: 0.4,
      neutralLower: -0.4,
      moderateUsdWeakness: -0.6,
      strongUsdWeakness: -1.2,
    },
    confidenceAdjustment: {
      type: "subtractive",
      condition: "Brent > P80",
      value: -0.05,
      rationale: "Oil shock = model breakdown risk",
    },
  },
};

/**
 * Get pair profile by label (e.g., "EURUSD")
 */
export function getPairProfile(label: string): PairProfile | undefined {
  return PAIR_PROFILES[label];
}

/**
 * Get driver tag for a pair — used in UI badges
 */
export function getDriverTag(label: string): string {
  return PAIR_PROFILES[label]?.driverTag ?? "Multi-factor";
}

/**
 * Get special signal label for display
 */
export function getSpecialSignalLabel(label: string): string {
  return PAIR_PROFILES[label]?.specialSignalLabel ?? "—";
}

/**
 * Format weight as percentage string
 */
export function fmtWeight(w: number): string {
  return `${Math.round(w * 100)}%`;
}

/**
 * All pair labels in canonical order
 */
export const PAIR_LABELS = Object.keys(PAIR_PROFILES) as string[];
