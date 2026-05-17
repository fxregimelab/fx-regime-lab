"use client";

import { useMemo } from "react";

export type DegradationLevel = "live" | "cached" | "stale" | "unavailable";

export interface DataFreshnessState {
  level: DegradationLevel;
  /** Age in minutes, or Infinity if no data. */
  ageMinutes: number;
  /** Human-readable age string. */
  ageText: string;
  /** Color token for the level. */
  color: string;
  /** Whether the data is considered usable. */
  usable: boolean;
}

function getLevel(ageMinutes: number): DegradationLevel {
  if (ageMinutes === Number.POSITIVE_INFINITY) return "unavailable";
  if (ageMinutes < 5) return "live";
  if (ageMinutes < 60) return "cached";
  return "stale";
}

function levelColor(level: DegradationLevel): string {
  switch (level) {
    case "live":
      return "var(--terminal-success)";
    case "cached":
      return "var(--terminal-fg-muted)";
    case "stale":
      return "var(--terminal-warning)";
    case "unavailable":
      return "var(--terminal-danger)";
  }
}

function levelLabel(level: DegradationLevel): string {
  switch (level) {
    case "live":
      return "LIVE";
    case "cached":
      return "CACHED";
    case "stale":
      return "STALE";
    case "unavailable":
      return "UNAVAILABLE";
  }
}

function fmtAge(minutes: number): string {
  if (minutes === Number.POSITIVE_INFINITY) return "—";
  if (minutes < 1) return "<1m";
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ${minutes % 60}m`;
  const days = Math.floor(hours / 24);
  return `${days}d ${hours % 24}h`;
}

/**
 * Hook that returns a 4-level degradation state for data freshness.
 *
 * Levels:
 * - live:    < 5 minutes old  → green halo
 * - cached:  5–60 minutes old → subtle timestamp
 * - stale:   > 60 minutes old → amber warning banner
 * - unavailable: no data      → red state + retry
 */
export function useDataFreshness(
  lastUpdatedAt: string | null | undefined,
): DataFreshnessState {
  return useMemo(() => {
    if (!lastUpdatedAt) {
      return {
        level: "unavailable",
        ageMinutes: Number.POSITIVE_INFINITY,
        ageText: "—",
        color: levelColor("unavailable"),
        usable: false,
      };
    }
    const ageMs = Date.now() - new Date(lastUpdatedAt).getTime();
    const ageMinutes = Math.max(0, Math.floor(ageMs / 60000));
    const level = getLevel(ageMinutes);
    return {
      level,
      ageMinutes,
      ageText: fmtAge(ageMinutes),
      color: levelColor(level),
      usable: level !== "unavailable",
    };
  }, [lastUpdatedAt]);
}

export { levelLabel };
