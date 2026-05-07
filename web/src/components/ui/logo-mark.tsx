"use client";

import React from "react";

interface LogoMarkProps {
  size?: number;
  color?: string;
}

export const LogoMark: React.FC<LogoMarkProps> = ({
  size = 28,
  color = "var(--terminal-fg, #e7e5e4)",
}) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 28 28"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="FX Regime Lab"
    >
      <rect
        x={2}
        y={2}
        width={24}
        height={24}
        rx={2}
        stroke={color}
        strokeWidth={1.5}
        fill="none"
      />
      <line x1={8} y1={8} x2={20} y2={20} stroke={color} strokeWidth={1.2} strokeLinecap="round" />
      <line x1={20} y1={8} x2={8} y2={20} stroke={color} strokeWidth={1.2} strokeLinecap="round" />
      <circle cx={14} cy={14} r={3} stroke={color} strokeWidth={1.2} fill="none" />
    </svg>
  );
};

export default LogoMark;
