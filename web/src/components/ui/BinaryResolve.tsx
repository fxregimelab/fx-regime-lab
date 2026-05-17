"use client";

import type React from "react";
import { useEffect, useRef, useState } from "react";

const HEX_CHARS = "0123456789ABCDEF";

interface BinaryResolveProps {
  value: string;
  resolveKey: string | number;
  paused?: boolean;
  flickerMs?: number;
  tickMs?: number;
}

export const BinaryResolve: React.FC<BinaryResolveProps> = ({
  value,
  resolveKey,
  paused = false,
  flickerMs = 300,
  tickMs = 45,
}) => {
  const [display, setDisplay] = useState<string>(value);
  const [resolved, setResolved] = useState(false);
  const [flashing, setFlashing] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // biome-ignore lint/correctness/useExhaustiveDependencies: flicker effect depends on value/paused only
  useEffect(() => {
    if (paused) {
      setDisplay(value);
      setResolved(true);
      return;
    }

    setResolved(false);
    setFlashing(false);
    setDisplay(
      value
        .split("")
        .map(() => HEX_CHARS[Math.floor(Math.random() * 16)])
        .join(""),
    );

    intervalRef.current = setInterval(() => {
      setDisplay(
        value
          .split("")
          .map(() => HEX_CHARS[Math.floor(Math.random() * 16)])
          .join(""),
      );
    }, tickMs);

    timeoutRef.current = setTimeout(() => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      setDisplay(value);
      setResolved(true);
      setFlashing(true);
      setTimeout(() => setFlashing(false), 250);
    }, flickerMs);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [resolveKey, value, paused, flickerMs, tickMs]);

  return (
    <span
      style={{
        fontFamily: "var(--font-mono), ui-monospace, monospace",
        fontVariantNumeric: "tabular-nums",
        color: flashing
          ? "#ffffff"
          : resolved
            ? undefined
            : "var(--terminal-fg-muted, #a8a29e)",
        transition: "color 150ms ease-out",
        textShadow: flashing ? "0 0 8px rgba(255,255,255,0.5)" : undefined,
      }}
      aria-label={value}
    >
      {display}
    </span>
  );
};

export default BinaryResolve;
