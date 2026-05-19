"use client";

import { useEffect, useState } from "react";

const HEX = "0123456789ABCDEF";

type GhostResolveProps = {
  value: string;
  className?: string;
  resolveKey?: string | number | null;
  /** When false, shows resolved ghost text without hex materialization. */
  active?: boolean;
  /** Skip flicker and show immediately (e.g. background cards in a Mosaic). */
  paused?: boolean;
};

const FLICKER_MS = 600;
const TICK_MS = 80;

function resolvedLen(s: string): number {
  const t = s.trim();
  if (!t) return 0;
  return Math.max(4, t.length);
}

function randomHex(len: number): string {
  let out = "";
  for (let i = 0; i < len; i++) out += HEX[Math.floor(Math.random() * 16)];
  return out;
}

/** Slower BinaryResolve variant — terminal whispers, muted final luminance. */
export function GhostResolve({
  value,
  className = "",
  resolveKey,
  active = true,
  paused = false,
}: GhostResolveProps) {
  const [display, setDisplay] = useState(value);
  const [phase, setPhase] = useState<"idle" | "flicker" | "resolved">("idle");

  useEffect(() => {
    const trimmed = value.trim();
    if (paused || !active) {
      setDisplay(trimmed);
      setPhase("resolved");
      return;
    }
    if (!trimmed) {
      setDisplay("");
      setPhase("idle");
      return;
    }

    const len = resolvedLen(value);
    let elapsed = 0;
    setPhase("flicker");
    setDisplay(randomHex(len));

    const iv = setInterval(() => {
      elapsed += TICK_MS;
      if (elapsed >= FLICKER_MS) {
        clearInterval(iv);
        setDisplay(trimmed);
        setPhase("resolved");
      } else {
        setDisplay(randomHex(len));
      }
    }, TICK_MS);

    return () => clearInterval(iv);
  }, [value, active, paused]);

  const ghostMuted = phase === "resolved" || !active;
  const flickerStyle =
    phase === "flicker" ? "text-[var(--color-text-dim)] opacity-50" : "";

  return (
    <span
      className={`inline-block font-mono text-[10px] tracking-widest tabular-nums will-change-[contents,opacity,color] ${
        ghostMuted ? "text-[var(--color-text-muted)] opacity-60" : flickerStyle
      } ${className}`.trim()}
    >
      {display}
    </span>
  );
}
