"use client";

import {
  type DegradationLevel,
  useDataFreshness,
} from "@/hooks/use-data-freshness";

interface DataFreshnessWrapperProps {
  /** ISO timestamp of last data update. */
  lastUpdatedAt: string | null | undefined;
  children: React.ReactNode;
  /** Called when user clicks retry in the unavailable state. */
  onRetry?: () => void;
  /** Optional source label (e.g. "Supabase"). */
  source?: string;
  /** Minimum level to trigger a visible banner. Default: "stale". */
  bannerThreshold?: DegradationLevel;
}

/**
 * Graceful Degradation Ladder — wraps content with appropriate UI
 * based on data freshness level.
 *
 * Level 1 (live <5m):    green halo around children
 * Level 2 (cached <1h):  subtle timestamp overlay
 * Level 3 (stale >1h):   amber warning banner above children
 * Level 4 (unavailable): red state with explanation + retry
 */
export function DataFreshnessWrapper({
  lastUpdatedAt,
  children,
  onRetry,
  source,
  bannerThreshold = "stale",
}: DataFreshnessWrapperProps) {
  const { level, ageText, color, usable } = useDataFreshness(lastUpdatedAt);

  // Level 4: No data — red state + explanation + retry
  if (level === "unavailable") {
    return (
      <div className="border border-[var(--terminal-danger)] bg-[var(--terminal-bg-sunken)] p-6 text-center">
        <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--terminal-danger)] uppercase mb-2">
          [ DATA UNAVAILABLE ]
        </p>
        <p className="font-mono text-[9px] text-[var(--terminal-fg-dim)] leading-relaxed max-w-md mx-auto mb-4">
          {source
            ? `Unable to fetch data from ${source}. The service may be temporarily unavailable.`
            : "Unable to fetch data. The service may be temporarily unavailable."}
        </p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="font-mono text-[9px] tracking-widest border border-[var(--terminal-danger)] text-[var(--terminal-danger)] px-3 py-1.5 hover:bg-[var(--terminal-danger)]/10 transition-colors cursor-pointer"
          >
            RETRY
          </button>
        )}
      </div>
    );
  }

  const showBanner =
    level === "stale" ||
    (level === "cached" && bannerThreshold === "cached") ||
    (level === "live" && bannerThreshold === "live");

  return (
    <div className="relative">
      {/* Level 3: Amber warning banner for stale data */}
      {showBanner && level === "stale" && (
        <div
          className="border-b border-[var(--terminal-warning)] bg-[var(--terminal-bg-elevated)] px-4 py-2 mb-0"
          role="alert"
          aria-live="polite"
        >
          <div className="flex items-center gap-2">
            <span
              className="inline-block h-1.5 w-1.5"
              style={{ background: "var(--terminal-warning)" }}
            />
            <span className="font-mono text-[9px] tracking-widest text-[var(--terminal-warning)] uppercase">
              STALE DATA · {ageText} OLD
            </span>
          </div>
          {source && (
            <p className="font-mono text-[9px] text-[var(--terminal-fg-dim)] mt-0.5">
              Source: {source} · Last update:{" "}
              {lastUpdatedAt?.slice(0, 19) ?? "unknown"}
            </p>
          )}
        </div>
      )}

      {/* Level 2: Subtle timestamp for cached data */}
      {level === "cached" && (
        <div className="absolute top-0 right-0 z-10 px-2 py-1">
          <span
            className="font-mono text-[9px] tracking-wider tabular-nums"
            style={{ color }}
          >
            {ageText}
          </span>
        </div>
      )}

      {/* Children with conditional halo */}
      <div
        className={
          level === "live"
            ? "ring-1 ring-[var(--terminal-success)]/30"
            : level === "stale"
              ? "ring-1 ring-[var(--terminal-warning)]/20"
              : ""
        }
      >
        {/* Level 1: Live indicator dot */}
        {level === "live" && (
          <div className="absolute top-0 right-0 z-10 px-2 py-1 flex items-center gap-1.5">
            <span
              className="h-1.5 w-1.5 animate-pulse"
              style={{ background: color }}
            />
            <span
              className="font-mono text-[9px] tracking-wider"
              style={{ color }}
            >
              LIVE
            </span>
          </div>
        )}
        {children}
      </div>
    </div>
  );
}
