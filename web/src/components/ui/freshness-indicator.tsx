"use client";

import { useMemo } from "react";

export type FreshnessLevel = "fresh" | "aging" | "stale";

interface FreshnessIndicatorProps {
  /** ISO timestamp of last data update. */
  lastUpdatedAt: string | null | undefined;
  /** If true, renders a pulsing dot. If false, renders text badge. */
  dot?: boolean;
  /** Optional label prefix. */
  label?: string;
}

function getFreshnessLevel(ageMinutes: number): FreshnessLevel {
  if (ageMinutes < 5) return "fresh";
  if (ageMinutes < 30) return "aging";
  return "stale";
}

function freshnessColor(level: FreshnessLevel): string {
  switch (level) {
    case "fresh":
      return "var(--terminal-success)";
    case "aging":
      return "var(--terminal-warning)";
    case "stale":
      return "var(--terminal-danger)";
  }
}

function freshnessLabel(level: FreshnessLevel): string {
  switch (level) {
    case "fresh":
      return "LIVE";
    case "aging":
      return "AGING";
    case "stale":
      return "STALE";
  }
}

/** Computes data freshness from an ISO timestamp. */
export function useFreshness(lastUpdatedAt: string | null | undefined): {
  level: FreshnessLevel;
  ageMinutes: number;
  color: string;
} {
  return useMemo(() => {
    if (!lastUpdatedAt) {
      return {
        level: "stale",
        ageMinutes: Number.POSITIVE_INFINITY,
        color: freshnessColor("stale"),
      };
    }
    const ageMs = Date.now() - new Date(lastUpdatedAt).getTime();
    const ageMinutes = Math.max(0, Math.floor(ageMs / 60000));
    const level = getFreshnessLevel(ageMinutes);
    return { level, ageMinutes, color: freshnessColor(level) };
  }, [lastUpdatedAt]);
}

/** Small freshness indicator — dot or text badge.
 *  Green: <5min  |  Amber: 5–30min  |  Red: >30min
 */
export function FreshnessIndicator({
  lastUpdatedAt,
  dot = true,
  label,
}: FreshnessIndicatorProps) {
  const { level, ageMinutes, color } = useFreshness(lastUpdatedAt);

  if (dot) {
    return (
      <span
        className="inline-flex items-center gap-1.5"
        title={`Data age: ${ageMinutes}m`}
      >
        <span
          className={`h-1.5 w-1.5 ${level === "fresh" ? "animate-pulse" : ""}`}
          style={{ background: color }}
        />
        {label && (
          <span
            className="font-mono text-[9px] tracking-wider"
            style={{ color }}
          >
            {label}
          </span>
        )}
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-1 border px-1.5 py-0.5 font-mono text-[9px] tracking-widest"
      style={{
        borderColor: color,
        color,
        borderRadius: 2,
      }}
    >
      <span
        className={`h-1 w-1 ${level === "fresh" ? "animate-pulse" : ""}`}
        style={{ background: color }}
      />
      {freshnessLabel(level)} · {ageMinutes}m
    </span>
  );
}

/** Warning banner for stale data (>30min). */
export function StaleDataBanner({
  lastUpdatedAt,
  source,
}: {
  lastUpdatedAt: string | null | undefined;
  source?: string;
}) {
  const { level, ageMinutes } = useFreshness(lastUpdatedAt);
  if (level !== "stale") return null;

  return (
    <div
      className="border border-[var(--terminal-danger)] bg-[var(--terminal-bg-sunken)] px-4 py-2 font-mono"
      role="alert"
      aria-live="polite"
    >
      <p className="text-[10px] tracking-widest text-[var(--terminal-danger)] uppercase">
        [ DATA STALE · {ageMinutes}m OLD ]
      </p>
      {source && (
        <p className="text-[9px] text-[var(--terminal-fg-dim)] mt-0.5">
          Source: {source} · Last update:{" "}
          {lastUpdatedAt?.slice(0, 19) ?? "unknown"}
        </p>
      )}
    </div>
  );
}

/** Conditional halo class for stale card borders. */
export function freshnessHaloClass(level: FreshnessLevel): string {
  switch (level) {
    case "fresh":
      return "";
    case "aging":
      return "ring-1 ring-[var(--terminal-warning)]/30";
    case "stale":
      return "ring-1 ring-[var(--terminal-danger)]/40";
  }
}
