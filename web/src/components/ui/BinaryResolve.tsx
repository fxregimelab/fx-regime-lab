"use client";

import { useEffect, useState } from "react";

const HEX = "0123456789ABCDEF";

type BinaryResolveProps = {
  /** Resolved display string (mono / tabular). */
  value: string;
  className?: string;
  /** When this changes, flicker re-runs (e.g. underlying number). */
  resolveKey?: string | number | null;
  /** If true, skips flicker and shows value immediately (used for background cards). */
  paused?: boolean;
  /** Override default flicker window (e.g. command palette handshake). */
  flickerMs?: number;
  /** Override tick interval. */
  tickMs?: number;
  /** If false, skip the brief white luminance snap after resolve. */
  resolveFlash?: boolean;
};

function resolvedLen(s: string): number {
  const t = s.trim();
  if (!t || t === "—" || t === "N/A") return 0;
  return Math.max(4, t.length);
}

function randomHex(len: number): string {
  let out = "";
  for (let i = 0; i < len; i++) out += HEX[Math.floor(Math.random() * 16)];
  return out;
}

const DEFAULT_FLICKER_MS = 300;
const DEFAULT_TICK_MS = 45;

/** Primary values resolve from hex noise → literal with a brief luminance snap. */
export function BinaryResolve({
  value,
  className = "",
  resolveKey,
  paused = false,
  flickerMs = DEFAULT_FLICKER_MS,
  tickMs = DEFAULT_TICK_MS,
  resolveFlash = true,
}: BinaryResolveProps) {
  const [display, setDisplay] = useState(value);
  const [flash, setFlash] = useState(false);

  useEffect(() => {
    if (paused) {
      setDisplay(value);
      setFlash(false);
      return;
    }

    const trimmed = value.trim();
    const skip = !trimmed || trimmed === "—" || trimmed === "N/A";
    if (skip) {
      setDisplay(value);
      setFlash(false);
      return;
    }

    const len = resolvedLen(value);
    let elapsed = 0;
    setFlash(false);
    setDisplay(randomHex(len));

    const iv = setInterval(() => {
      elapsed += tickMs;
      if (elapsed >= flickerMs) {
        clearInterval(iv);
        setDisplay(value);
        if (resolveFlash) {
          setFlash(true);
          const t = window.setTimeout(() => setFlash(false), 200);
          return () => window.clearTimeout(t);
        }
      } else {
        setDisplay(randomHex(len));
      }
    }, tickMs);

    return () => {
      clearInterval(iv);
    };
  }, [value, paused, flickerMs, tickMs, resolveFlash]);

  return (
    <span
      className={`inline-block font-mono tabular-nums will-change-[contents,color] ${
        flash ? "text-white" : ""
      } ${className}`.trim()}
    >
      {display}
    </span>
  );
}
