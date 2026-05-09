interface StatsCardProps {
  label: string;
  value: string;
  sub?: string;
  delta?: number | null;
  stale?: boolean;
}

export function StatsCard({ label, value, sub, delta, stale }: StatsCardProps) {
  const deltaColor =
    delta == null
      ? "var(--color-text-muted)"
      : delta >= 0
        ? "var(--color-up)"
        : "var(--color-down)";

  return (
    <div
      className={`bg-[var(--color-surface)] p-5 md:p-6 ${stale ? "opacity-50" : ""}`}
    >
      <p className="font-mono text-[9px] tracking-[0.12em] text-[var(--color-text-muted)] uppercase mb-2.5">
        {label}
      </p>
      <p className="font-mono text-[clamp(22px,3vw,28px)] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">
        {value}
      </p>
      <div className="flex items-center gap-2 mt-1.5">
        {sub && (
          <p className="font-mono text-[10px] text-[var(--color-text-muted)] tabular-nums">
            {sub}
          </p>
        )}
        {delta != null && (
          <p
            className="font-mono text-[10px] tabular-nums"
            style={{ color: deltaColor }}
          >
            {delta >= 0 ? "+" : ""}
            {delta.toFixed(2)} vs prior
          </p>
        )}
      </div>
    </div>
  );
}
