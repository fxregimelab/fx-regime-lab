"use client";

import React from "react";

type TerminalLabelProps = {
  children: string;
  limit?: number;
  className?: string;
  prefix?: string;
  suffix?: string;
};

/**
 * OMEGA TerminalLabel: Enforces character budgeting and rigid mono spacing.
 * Ensures that long labels don't break the horizontal rhythm of the grid.
 */
export function TerminalLabel({
  children,
  limit = 12,
  className = "",
  prefix = "",
  suffix = "",
}: TerminalLabelProps) {
  const display =
    children.length > limit
      ? `${children.slice(0, limit - 1).trim()}…`
      : children;

  return (
    <span
      className={`font-mono text-[9px] tracking-widest uppercase tabular-nums whitespace-nowrap overflow-hidden ${className}`}
      title={children.length > limit ? children : undefined}
    >
      {prefix}
      {display}
      {suffix}
    </span>
  );
}
