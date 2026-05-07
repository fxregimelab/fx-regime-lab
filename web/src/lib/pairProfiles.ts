import { PAIR_SLUGS, PAIR_DISPLAY, PAIR_COLORS } from "./constants";
import type { PairSlug } from "./constants";

export interface PairProfile {
  slug: PairSlug;
  display: string;
  color: string;
  spotDecimals: number;
  pipMultiplier: number;
  signalWeight: number;
}

export const PAIR_PROFILES: Record<PairSlug, PairProfile> = {
  "eur-usd": {
    slug: "eur-usd",
    display: PAIR_DISPLAY["eur-usd"],
    color: PAIR_COLORS["eur-usd"],
    spotDecimals: 5,
    pipMultiplier: 10000,
    signalWeight: 1.0,
  },
  "usd-jpy": {
    slug: "usd-jpy",
    display: PAIR_DISPLAY["usd-jpy"],
    color: PAIR_COLORS["usd-jpy"],
    spotDecimals: 3,
    pipMultiplier: 100,
    signalWeight: 1.0,
  },
  "usd-inr": {
    slug: "usd-inr",
    display: PAIR_DISPLAY["usd-inr"],
    color: PAIR_COLORS["usd-inr"],
    spotDecimals: 4,
    pipMultiplier: 10000,
    signalWeight: 0.8,
  },
};

export function getPairProfile(slug: string): PairProfile | null {
  if (PAIR_SLUGS.includes(slug as PairSlug)) {
    return PAIR_PROFILES[slug as PairSlug];
  }
  return null;
}

export function formatSpotForPair(spot: number, slug: string): string {
  const profile = getPairProfile(slug);
  const decimals = profile?.spotDecimals ?? 4;
  return spot.toFixed(decimals);
}

export function pipsForPair(
  entry: number,
  current: number,
  slug: string
): number {
  const profile = getPairProfile(slug);
  const mult = profile?.pipMultiplier ?? 10000;
  return (current - entry) * mult;
}

export function weightedSignalScore(
  confidence: number,
  slug: string
): number {
  const profile = getPairProfile(slug);
  const weight = profile?.signalWeight ?? 1.0;
  return confidence * weight;
}

/** Driver tag lookup by canonical label (EURUSD, USDJPY, USDINR). */
const DRIVER_TAGS: Record<string, string> = {
  EURUSD: "Rates-driven",
  USDJPY: "Funding-driven",
  USDINR: "Carry-sensitive",
};

export function getDriverTag(label: string): string {
  return DRIVER_TAGS[label] ?? "Multi-factor";
}

/** Get special signal label for display (legacy compatibility). */
const SPECIAL_LABELS: Record<string, string> = {
  EURUSD: "ECB_sentiment",
  USDJPY: "JPY_funding_stress",
  USDINR: "EM_carry_RBI",
};

export function getSpecialSignalLabel(label: string): string {
  return SPECIAL_LABELS[label] ?? "—";
}

/** Format weight as percentage string. */
export function fmtWeight(w: number): string {
  return `${Math.round(w * 100)}%`;
}

/** All pair labels in canonical order. */
export const PAIR_LABELS = Object.keys(DRIVER_TAGS);
