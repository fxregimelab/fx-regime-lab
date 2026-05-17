import { FreshnessIndicator } from "@/components/ui/freshness-indicator";
import { normalizeProp, timeAgo } from "@/components/ui/utils";

interface SystemStatusBarProps {
  dqs: number | null;
  stressLevel: string | null;
  lastRunAt: string | null;
  validatedCount: number | null;
}

export function SystemStatusBar({
  dqs,
  stressLevel,
  lastRunAt,
  validatedCount,
}: SystemStatusBarProps) {
  const dqsProp = normalizeProp(dqs);
  const dqsColor =
    dqsProp == null
      ? "var(--color-text-muted)"
      : dqsProp >= 0.75
        ? "var(--color-up)"
        : dqsProp >= 0.5
          ? "var(--color-warn)"
          : "var(--color-down)";

  const stressColor =
    stressLevel === "RED"
      ? "var(--color-down)"
      : stressLevel === "AMBER"
        ? "var(--color-warn)"
        : stressLevel === "GREEN"
          ? "var(--color-up)"
          : "var(--color-text-muted)";

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[var(--color-border)] border border-[var(--color-border)] mb-10">
      {/* DQS Gauge */}
      <div className="bg-[var(--color-surface)] p-4 md:p-5">
        <div className="flex items-center justify-between mb-2">
          <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
            DQS
          </p>
          <p
            className="font-mono text-[clamp(18px,2.5vw,24px)] font-medium tracking-tight leading-none tabular-nums"
            style={{ color: dqsColor }}
          >
            {dqsProp != null ? dqsProp.toFixed(2) : "—"}
          </p>
        </div>
        {/* Visual gauge */}
        <div className="h-[4px] w-full bg-[var(--terminal-bg-sunken)] overflow-hidden">
          <div
            className="h-full transition-all duration-700"
            style={{
              width: `${(dqsProp ?? 0) * 100}%`,
              background: dqsColor,
            }}
          />
        </div>
        <p className="font-mono text-[9px] text-[var(--color-text-dim)] mt-1">
          {dqsProp == null
            ? "—"
            : dqsProp >= 0.9
              ? "EXCELLENT"
              : dqsProp >= 0.8
                ? "GOOD"
                : dqsProp >= 0.6
                  ? "FAIR"
                  : "POOR"}
        </p>
      </div>

      {/* Stress Badge */}
      <div className="bg-[var(--color-surface)] p-4 md:p-5 flex items-center justify-between">
        <div>
          <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-1">
            STRESS
          </p>
          <p
            className="font-mono text-[clamp(18px,2.5vw,24px)] font-medium tracking-tight leading-none tabular-nums"
            style={{ color: stressColor }}
          >
            {stressLevel ?? "—"}
          </p>
        </div>
        <div className="w-2 h-8" style={{ background: stressColor }} />
      </div>

      {/* Last Run */}
      <div className="bg-[var(--color-surface)] p-4 md:p-5">
        <div className="flex items-center gap-2 mb-1">
          <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
            LAST RUN
          </p>
          <FreshnessIndicator lastUpdatedAt={lastRunAt} dot />
        </div>
        <p className="font-mono text-[clamp(18px,2.5vw,24px)] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">
          {lastRunAt ? timeAgo(lastRunAt) : "—"}
        </p>
      </div>

      {/* Validated Calls */}
      <div className="bg-[var(--color-surface)] p-4 md:p-5">
        <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-1">
          VALIDATED
        </p>
        <p className="font-mono text-[clamp(18px,2.5vw,24px)] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">
          {validatedCount != null ? validatedCount.toString() : "—"}
        </p>
        <p className="font-mono text-[9px] text-[var(--color-text-muted)] mt-1">
          T+5 calls
        </p>
      </div>
    </div>
  );
}
