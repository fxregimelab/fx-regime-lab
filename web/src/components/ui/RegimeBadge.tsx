"use client";

import Link from "next/link";

interface RegimeBadgeProps {
  regime: string;
  category?: string;
  size?: "sm" | "md";
  showLink?: boolean;
}

const CATEGORY_COLORS: Record<string, string> = {
  RATE_DRIVEN: "var(--color-text)",
  CARRY_DRIVEN: "var(--color-brand-amber)",
  VOLATILITY_DRIVEN: "var(--color-regime-uncertain)",
  POLICY_SHOCK: "var(--color-regime-bearish)",
  LIQUIDITY_SHOCK: "var(--color-down)",
  NEUTRAL: "var(--color-regime-neutral)",
};

export function RegimeBadge({
  regime,
  category,
  size = "md",
  showLink = true,
}: RegimeBadgeProps) {
  const display = regime.replace(/_/g, " ");
  const color = category ? CATEGORY_COLORS[category] : "var(--color-text)";

  const sizeClasses = {
    sm: "text-[10px] px-2 py-0.5",
    md: "text-[11px] px-2.5 py-1",
  };

  const content = (
    <span
      className={`inline-block font-sans font-medium tracking-wide border ${sizeClasses[size]}`}
      style={{
        color,
        borderColor: color,
        borderRadius: 2,
      }}
      title={category ? `${display} — ${category.replace(/_/g, " ")}` : display}
    >
      {display}
    </span>
  );

  if (showLink) {
    return (
      <Link
        href="/methodology"
        className="inline-block hover:opacity-80 transition-opacity"
      >
        {content}
      </Link>
    );
  }

  return content;
}
