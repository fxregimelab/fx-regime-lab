import { timeAgo } from "@/components/ui/utils";

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
  const dqsColor =
    dqs == null
      ? "var(--color-text-muted)"
      : dqs >= 0.75
        ? "var(--color-up)"
        : dqs >= 0.5
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
      <div className="bg-[var(--color-surface)] p-4 md:p-5 flex items-center justify-between">
        <div>
          <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-1">
            DQS
          </p>
          <p
            className="font-mono text-[clamp(18px,2.5vw,24px)] font-medium tracking-tight leading-none tabular-nums"
            style={{ color: dqsColor }}
          >
            {dqs != null ? dqs.toFixed(2) : "—"}
          </p>
        </div>
        <div
          className="w-2 h-8"
          style={{
            background:
              dqs == null
                ? "#333"
                : `linear-gradient(to top, ${dqsColor} ${Math.round((dqs ?? 0) * 100)}%, #1e1e1e ${Math.round((dqs ?? 0) * 100)}%)`,
          }}
        />
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
        <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-1">
          LAST RUN
        </p>
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
