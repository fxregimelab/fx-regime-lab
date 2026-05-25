"use client";

interface MetricCardProps {
  label: string;
  value: string;
  sub?: string;
  context?: string;
  size?: "sm" | "md" | "lg";
  highlight?: boolean;
}

export function MetricCard({
  label,
  value,
  sub,
  context,
  size = "md",
  highlight = false,
}: MetricCardProps) {
  const sizeClasses = {
    sm: {
      value: "text-[clamp(20px,3vw,28px)]",
      label: "text-[9px]",
      padding: "py-6 px-5",
    },
    md: {
      value: "text-[clamp(28px,4vw,40px)]",
      label: "text-[10px]",
      padding: "py-8 px-6",
    },
    lg: {
      value: "text-[clamp(36px,5vw,56px)]",
      label: "text-[10px]",
      padding: "py-10 px-8",
    },
  };

  const s = sizeClasses[size];

  return (
    <div
      className={`${s.padding} bg-[var(--color-surface)] cursor-default transition-all duration-300 hover:bg-[var(--color-surface-depth-2)] ${
        highlight ? "border border-[var(--color-brand-amber-muted)]" : ""
      }`}
    >
      <p
        className={`font-sans ${s.value} font-semibold text-[var(--color-text)] tracking-tight leading-none mb-3 tabular-nums`}
      >
        {value}
      </p>
      <p
        className={`font-sans ${s.label} tracking-[0.2em] text-[var(--color-text-muted)] uppercase leading-relaxed mb-1`}
      >
        {label}
      </p>
      {sub && (
        <p className="font-sans text-[11px] text-[var(--color-text-secondary)]">
          {sub}
        </p>
      )}
      {context && (
        <p className="font-sans text-[10px] text-[var(--color-text-dim)] mt-2">
          {context}
        </p>
      )}
    </div>
  );
}
