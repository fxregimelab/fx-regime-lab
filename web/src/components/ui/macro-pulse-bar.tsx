"use client";

import type React from "react";
import { useMemo } from "react";

interface MacroPulseBarProps {
  dxy?: number;
  us10y?: number;
  vix?: number;
  wti?: number;
}

export const MacroPulseBar: React.FC<MacroPulseBarProps> = ({
  dxy = 0,
  us10y = 0,
  vix = 0,
  wti = 0,
}) => {
  const items = useMemo(
    () => [
      { label: "DXY", value: dxy, decimals: 2 },
      { label: "US10Y", value: us10y, decimals: 2 },
      { label: "VIX", value: vix, decimals: 2 },
      { label: "WTI", value: wti, decimals: 2 },
    ],
    [dxy, us10y, vix, wti],
  );

  const content = (
    <div
      style={{
        display: "flex",
        gap: "var(--space-8, 2rem)",
        whiteSpace: "nowrap",
      }}
    >
      {items.map((item) => (
        <span
          key={item.label}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "var(--space-1-5, 0.375rem)",
            fontFamily: "var(--font-mono), ui-monospace, monospace",
            fontVariantNumeric: "tabular-nums",
            fontSize: "var(--text-xs, 0.6875rem)",
            color: "var(--terminal-fg-muted, #a8a29e)",
          }}
        >
          <span style={{ color: "var(--terminal-fg-dim, #78716c)" }}>
            {item.label}
          </span>
          <span style={{ color: "var(--terminal-fg, #e7e5e4)" }}>
            {item.value.toFixed(item.decimals)}
          </span>
        </span>
      ))}
    </div>
  );

  return (
    <div
      style={{
        borderTop: "1px solid var(--terminal-border, #292524)",
        borderBottom: "1px solid var(--terminal-border, #292524)",
        background: "var(--terminal-bg-sunken, #0a0807)",
        padding: "var(--space-2, 0.5rem) 0",
        overflow: "hidden",
      }}
      data-surface="terminal"
    >
      <div
        className="animate-ticker-marquee"
        style={{
          display: "flex",
          width: "max-content",
        }}
      >
        {content}
        {content}
        {content}
        {content}
      </div>
    </div>
  );
};

export default MacroPulseBar;
