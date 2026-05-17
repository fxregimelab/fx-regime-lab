import { normalizeProp } from "./utils";

interface ConfidenceBarProps {
  value?: number | null;
  tone?: "dark" | "light";
  color?: string;
}

export function ConfidenceBar({
  value,
  tone = "dark",
  color,
}: ConfidenceBarProps) {
  const prop = normalizeProp(value) ?? 0;
  const pct =
    value == null ? 0 : Math.min(100, Math.max(0, Math.round(prop * 100)));
  const barColor = color || "var(--color-warn)";
  const trackColor =
    tone === "dark" ? "var(--color-elevated)" : "var(--color-surface)";

  return (
    <div
      style={{
        background: trackColor,
        height: tone === "dark" ? 3 : 2,
        width: "100%",
      }}
    >
      <div
        style={{
          width: `${pct}%`,
          height: "100%",
          background: barColor,
          transition: "width 0.5s ease",
        }}
      />
    </div>
  );
}
