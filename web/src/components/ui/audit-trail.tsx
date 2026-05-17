"use client";

import { useEffect, useState } from "react";
import { timeAgo } from "./utils";

export interface AuditTrailBannerProps {
  /** ISO timestamp of last pipeline run. */
  lastRunAt: string | null;
  /** Pipeline status. */
  status?: "HEALTHY" | "DEGRADED" | "FAILED" | "UNKNOWN";
  /** Data Quality Score (0–1). */
  dqs?: number | null;
  /** Visual variant: terminal (footer) vs shell (header). */
  variant: "terminal" | "shell";
}

/**
 * Audit Trail Banner — always-visible integrity indicator.
 *
 * Terminal pages: subtle footer banner
 * Shell pages: subtle header banner
 *
 * Displays: "System integrity verified: TIMESTAMP · Pipeline: OK · DQS: X.XX"
 */
export function AuditTrailBanner({
  lastRunAt,
  status = "UNKNOWN",
  dqs,
  variant,
}: AuditTrailBannerProps) {
  const [mounted, setMounted] = useState(false);

  // Avoid hydration mismatch for time-ago
  useEffect(() => {
    setMounted(true);
  }, []);

  const statusText =
    status === "HEALTHY"
      ? "OK"
      : status === "DEGRADED"
        ? "DEGRADED"
        : status === "FAILED"
          ? "FAILED"
          : "UNKNOWN";

  const statusColor =
    status === "HEALTHY"
      ? "var(--terminal-success)"
      : status === "DEGRADED"
        ? "var(--terminal-warning)"
        : "var(--terminal-danger)";

  const dqsText = dqs != null ? dqs.toFixed(2) : "—";

  const timestamp =
    mounted && lastRunAt
      ? timeAgo(lastRunAt)
      : (lastRunAt?.slice(0, 19) ?? "—");

  if (variant === "terminal") {
    return (
      <div className="border-t border-[var(--terminal-border)] bg-[var(--terminal-bg-sunken)] px-4 py-2">
        <div className="max-w-[1152px] mx-auto flex items-center justify-between flex-wrap gap-2">
          <p className="font-mono text-[9px] tracking-wider text-[var(--terminal-fg-dim)]">
            <span className="text-[var(--terminal-fg-muted)]">
              System integrity verified:
            </span>{" "}
            <span className="tabular-nums">{timestamp}</span>
          </p>
          <div className="flex items-center gap-3">
            <span className="font-mono text-[9px] tracking-wider text-[var(--terminal-fg-dim)]">
              Pipeline: <span style={{ color: statusColor }}>{statusText}</span>
            </span>
            <span className="font-mono text-[9px] tracking-wider text-[var(--terminal-fg-dim)]">
              DQS:{" "}
              <span className="tabular-nums text-[var(--terminal-fg-muted)]">
                {dqsText}
              </span>
            </span>
          </div>
        </div>
      </div>
    );
  }

  // shell variant
  return (
    <div className="border-b border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-1.5">
      <div className="max-w-[1152px] mx-auto flex items-center justify-between flex-wrap gap-2">
        <p className="font-mono text-[9px] tracking-wider text-[var(--color-text-muted)]">
          <span className="text-[var(--color-text-secondary)]">
            System integrity verified:
          </span>{" "}
          <span className="tabular-nums">{timestamp}</span>
        </p>
        <div className="flex items-center gap-3">
          <span className="font-mono text-[9px] tracking-wider text-[var(--color-text-muted)]">
            Pipeline: <span style={{ color: statusColor }}>{statusText}</span>
          </span>
          <span className="font-mono text-[9px] tracking-wider text-[var(--color-text-muted)]">
            DQS:{" "}
            <span className="tabular-nums text-[var(--color-text)]">
              {dqsText}
            </span>
          </span>
        </div>
      </div>
    </div>
  );
}
