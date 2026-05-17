"use client";

import { useState } from "react";
import { timeAgo } from "./utils";

export interface CircuitBreakerProps {
  /** ISO timestamp of last successful pipeline run. */
  lastRunAt: string | null;
  /** Pipeline status from health check. */
  status?: "HEALTHY" | "DEGRADED" | "FAILED" | "UNKNOWN";
  /** Human-readable errors, if any. */
  errors?: string[];
  /** Expected pipeline run hour (UTC). Default: 8. */
  expectedHourUtc?: number;
}

/** Compute next expected run time based on last run + expected hour. */
function nextExpectedRun(
  lastRunAt: string | null,
  expectedHourUtc: number,
): string {
  const now = new Date();
  const today = new Date(
    Date.UTC(
      now.getUTCFullYear(),
      now.getUTCMonth(),
      now.getUTCDate(),
      expectedHourUtc,
    ),
  );
  const tomorrow = new Date(today.getTime() + 24 * 60 * 60 * 1000);

  // If today's expected time hasn't passed yet, that's the next run
  if (now.getTime() < today.getTime()) {
    return `${today.toISOString().slice(0, 16).replace("T", " ")} UTC`;
  }
  return `${tomorrow.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

/** True if the circuit should trip (no data or pipeline failed). */
function isTripped(
  lastRunAt: string | null,
  status?: CircuitBreakerProps["status"],
): boolean {
  if (status === "FAILED" || status === "UNKNOWN") return true;
  if (!lastRunAt) return true;
  // Trip if last run is older than 25 hours (expected daily)
  const ageHours = (Date.now() - new Date(lastRunAt).getTime()) / 3600000;
  return ageHours > 25;
}

/**
 * Circuit Breaker UI — red border + warning banner when pipeline hasn't run.
 *
 * Shows "Last successful run: Xh ago · Expected next: 08:00 UTC".
 * Click banner to expand pipeline health details.
 */
export function CircuitBreaker({
  lastRunAt,
  status = "UNKNOWN",
  errors = [],
  expectedHourUtc = 8,
}: CircuitBreakerProps) {
  const [expanded, setExpanded] = useState(false);
  const tripped = isTripped(lastRunAt, status);

  if (!tripped) return null;

  const ageText = lastRunAt ? timeAgo(lastRunAt) : "UNKNOWN";
  const nextRun = nextExpectedRun(lastRunAt, expectedHourUtc);

  return (
    <div
      className="border border-[var(--terminal-danger)] bg-[var(--terminal-bg-sunken)]"
      role="alert"
      aria-live="assertive"
    >
      {/* Collapsed banner */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-left cursor-pointer hover:bg-[var(--terminal-bg-elevated)] transition-colors"
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-3">
          <span
            className="inline-block h-2 w-2 animate-pulse"
            style={{ background: "var(--terminal-danger)" }}
          />
          <span className="font-mono text-[10px] tracking-[0.15em] text-[var(--terminal-danger)] uppercase">
            [ PIPELINE INTERRUPTED ]
          </span>
          <span className="font-mono text-[9px] text-[var(--terminal-fg-dim)] tabular-nums hidden sm:inline">
            Last successful run: {ageText} · Expected next: {nextRun}
          </span>
        </div>
        <span className="font-mono text-[9px] text-[var(--terminal-fg-dim)]">
          {expanded ? "[−]" : "[+]"}
        </span>
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="border-t border-[var(--terminal-danger)]/30 px-4 py-3 space-y-2">
          <p className="font-mono text-[9px] text-[var(--terminal-fg-muted)] leading-relaxed">
            The daily regime pipeline has not completed its expected run.
            Signals shown may be stale or missing. The system will automatically
            resume when the pipeline completes.
          </p>

          <div className="grid grid-cols-2 gap-2 mt-2">
            <div>
              <p className="font-mono text-[9px] tracking-widest text-[var(--terminal-fg-dim)] uppercase">
                Status
              </p>
              <p
                className="font-mono text-[10px] tracking-wide"
                style={{
                  color:
                    status === "HEALTHY"
                      ? "var(--terminal-success)"
                      : status === "DEGRADED"
                        ? "var(--terminal-warning)"
                        : "var(--terminal-danger)",
                }}
              >
                {status}
              </p>
            </div>
            <div>
              <p className="font-mono text-[9px] tracking-widest text-[var(--terminal-fg-dim)] uppercase">
                Last Run
              </p>
              <p className="font-mono text-[10px] text-[var(--terminal-fg-muted)] tabular-nums">
                {lastRunAt?.slice(0, 19) ?? "—"} UTC
              </p>
            </div>
            <div>
              <p className="font-mono text-[9px] tracking-widest text-[var(--terminal-fg-dim)] uppercase">
                Next Expected
              </p>
              <p className="font-mono text-[10px] text-[var(--terminal-fg-muted)] tabular-nums">
                {nextRun}
              </p>
            </div>
            <div>
              <p className="font-mono text-[9px] tracking-widest text-[var(--terminal-fg-dim)] uppercase">
                Errors
              </p>
              <p className="font-mono text-[10px] text-[var(--terminal-fg-muted)]">
                {errors.length > 0 ? errors.length : "None"}
              </p>
            </div>
          </div>

          {errors.length > 0 && (
            <ul className="mt-2 space-y-1">
              {errors.map((err) => (
                <li
                  key={err}
                  className="font-mono text-[9px] text-[var(--terminal-danger)]"
                >
                  › {err}
                </li>
              ))}
            </ul>
          )}

          <div className="pt-2">
            <a
              href="/audit"
              className="font-mono text-[9px] tracking-widest text-[var(--terminal-fg-muted)] hover:text-[var(--terminal-fg)] underline underline-offset-2"
            >
              VIEW FULL AUDIT LOG →
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

/** Wraps children with a conditional red border when circuit is tripped. */
export function CircuitBreakerBorder({
  lastRunAt,
  status,
  errors,
  expectedHourUtc,
  children,
}: CircuitBreakerProps & { children: React.ReactNode }) {
  const tripped = isTripped(lastRunAt, status);

  return (
    <div className={tripped ? "ring-1 ring-[var(--terminal-danger)]" : ""}>
      <CircuitBreaker
        lastRunAt={lastRunAt}
        status={status}
        errors={errors}
        expectedHourUtc={expectedHourUtc}
      />
      {children}
    </div>
  );
}
