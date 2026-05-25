"use client";

interface ConfidenceMeterProps {
  confidence: number | null;
  size?: "sm" | "md";
  showLabel?: boolean;
}

function getConfidenceLabel(prop: number): string {
  if (prop >= 0.7) return "High";
  if (prop >= 0.5) return "Moderate";
  if (prop >= 0.3) return "Low";
  return "Very Low";
}

function getConfidenceColor(prop: number): string {
  if (prop >= 0.7) return "var(--color-regime-bullish)";
  if (prop >= 0.5) return "var(--color-brand-amber)";
  if (prop >= 0.3) return "var(--color-regime-uncertain)";
  return "var(--color-regime-bearish)";
}

export function ConfidenceMeter({
  confidence,
  size = "md",
  showLabel = true,
}: ConfidenceMeterProps) {
  if (confidence == null) {
    return (
      <div className="flex items-center gap-2">
        <span className="font-sans text-[13px] text-[var(--color-text-muted)]">
          —
        </span>
      </div>
    );
  }

  const pct = Math.min(100, Math.max(0, Math.round(confidence * 100)));
  const color = getConfidenceColor(confidence);
  const label = getConfidenceLabel(confidence);

  const height = size === "sm" ? "h-[2px]" : "h-[3px]";
  const width = size === "sm" ? "w-16" : "w-24";

  return (
    <div className="flex items-center gap-3">
      <div
        className={`${width} ${height} bg-[var(--color-border)] overflow-hidden`}
      >
        <div
          className="h-full transition-all duration-700 ease-out"
          style={{
            width: `${pct}%`,
            backgroundColor: color,
          }}
        />
      </div>
      {showLabel && (
        <span
          className="font-sans text-[11px] font-medium tabular-nums"
          style={{ color }}
        >
          {label}
        </span>
      )}
    </div>
  );
}
