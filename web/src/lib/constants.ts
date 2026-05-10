// Canonical pair metadata (object array — used by pages and components)
export const PAIRS = [
  {
    label: "EURUSD" as const,
    display: "EUR/USD",
    urlSlug: "eurusd",
    pairColor: "#4080e0",
  },
  {
    label: "USDJPY" as const,
    display: "USD/JPY",
    urlSlug: "usdjpy",
    pairColor: "#e08020",
  },
  {
    label: "USDINR" as const,
    display: "USD/INR",
    urlSlug: "usdinr",
    pairColor: "#c04020",
  },
];

export type PairMeta = (typeof PAIRS)[number];

// Canonical pair slugs (string array — used by new rebuild code)
export const PAIR_SLUGS = ["eur-usd", "usd-jpy", "usd-inr"] as const;
export type PairSlug = (typeof PAIR_SLUGS)[number];

export const PAIR_DISPLAY: Record<PairSlug, string> = {
  "eur-usd": "EUR / USD",
  "usd-jpy": "USD / JPY",
  "usd-inr": "USD / INR",
};

export const PAIR_COLORS: Record<PairSlug, string> = {
  "eur-usd": "#4080e0", // logo blue
  "usd-jpy": "#e08020", // logo orange
  "usd-inr": "#c04020", // logo red
};

// Merged regime heatmap colors (old + new regimes)
export const REGIME_HEATMAP_COLORS: Record<string, string> = {
  // Legacy regimes
  "STRONG USD STRENGTH": "#1e3a5f",
  "MODERATE USD STRENGTH": "#2d5a8e",
  NEUTRAL: "#3a3a3a",
  "MODERATE USD WEAKNESS": "#7a3f1f",
  "STRONG USD WEAKNESS": "#a0522d",
  VOL_EXPANDING: "#7a5c00",
  "STRONG DEPRECIATION PRESSURE": "#6b1a1a",
  "MODERATE DEPRECIATION PRESSURE": "#8b2a2a",
  "MODERATE APPRECIATION PRESSURE": "#1a5a2a",
  "STRONG APPRECIATION PRESSURE": "#0d3a1a",
  DIRECTIONAL_ONLY: "#333",
  UNKNOWN: "#1a1a1a",
  // New regimes
  TRENDING: "#10b981",
  RANGING: "#f59e0b",
  BREAKOUT: "#8b5cf6",
  REVERSAL: "#ef4444",
  ACCUMULATION: "#3b82f6",
  DISTRIBUTION: "#6366f1",
  VOLATILE: "#f97316",
  COMPRESSION: "#14b8a6",
};

export const BRAND = {
  name: "FX Regime Lab",
  tagline: "Institutional-grade regime detection for global FX markets",
  canonicalPairs: PAIRS,
  contact: {
    email: "desk@fxregimelab.com",
    twitter: "@fxregimelab",
  },
} as const;

export const CANONICAL_PAIRS_SET = new Set<string>(PAIR_SLUGS);
