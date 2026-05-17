"use client";

import { useDensityPreset } from "@/hooks/use-density-preset";

/**
 * Small indicator showing current density preset.
 * Click to cycle. Keyboard: 'd'.
 */
export function DensityIndicator() {
  const { preset, cyclePreset } = useDensityPreset();

  return (
    <button
      type="button"
      onClick={cyclePreset}
      className="font-mono text-[9px] tracking-widest text-[var(--terminal-fg-dim)] hover:text-[var(--terminal-fg)] transition-colors cursor-pointer"
      title={`Density: ${preset} (click or press 'd' to cycle)`}
    >
      [{preset.toUpperCase()}]
    </button>
  );
}
