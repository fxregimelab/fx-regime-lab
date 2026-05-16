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
  const pct = value == null ? 0 : Math.min(100, Math.max(0, Math.round(value * 100)));
  const barColor = color || "#F5923A";
  const trackColor = tone === "dark" ? "#1e1e1e" : "#ebebeb";

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
