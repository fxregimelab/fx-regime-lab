"use client";

interface SampleSizeBadgeProps {
  n: number | null | undefined;
  showWarning?: boolean;
}

/** Mono-font sample size badge.
 *  Shows n=XXX. Mutes styling when n < 30 (insufficient sample).
 */
export function SampleSizeBadge({
  n,
  showWarning = true,
}: SampleSizeBadgeProps) {
  if (n == null || !Number.isFinite(n)) {
    return (
      <span className="font-mono text-[9px] text-[var(--terminal-fg-dim)] tabular-nums">
        n=—
      </span>
    );
  }

  const isSmall = n < 30;

  if (showWarning && isSmall) {
    return (
      <span
        className="inline-flex items-center gap-1 font-mono text-[9px] tracking-wider tabular-nums"
        title="Sample size < 30 — low statistical confidence"
      >
        <span className="h-1.5 w-1.5 bg-[var(--terminal-warning)]" />
        <span className="text-[var(--terminal-warning)]">n={n}</span>
      </span>
    );
  }

  return (
    <span className="font-mono text-[9px] text-[var(--terminal-fg-muted)] tabular-nums">
      n={n}
    </span>
  );
}
