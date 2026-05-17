"use client";

import { useCallback, useEffect, useState } from "react";

export type DensityPreset = "compact" | "standard" | "relaxed";

const STORAGE_KEY = "fxrl-density-preset";
const DEFAULT_PRESET: DensityPreset = "standard";

function readPreset(): DensityPreset {
  if (typeof window === "undefined") return DEFAULT_PRESET;
  try {
    const stored = localStorage.getItem(STORAGE_KEY) as DensityPreset | null;
    if (stored && ["compact", "standard", "relaxed"].includes(stored)) {
      return stored;
    }
  } catch {
    // localStorage unavailable
  }
  return DEFAULT_PRESET;
}

function writePreset(preset: DensityPreset) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, preset);
  } catch {
    // localStorage unavailable
  }
}

/**
 * Data density preset hook.
 *
 * Three presets:
 * - Compact:  maximum data density
 * - Standard: balanced (default)
 * - Relaxed:  for presentations/screenshots
 *
 * Toggle with 'd' key or UI button.
 * Persisted in localStorage.
 */
export function useDensityPreset() {
  const [preset, setPresetState] = useState<DensityPreset>(DEFAULT_PRESET);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setPresetState(readPreset());
    setMounted(true);
  }, []);

  const setPreset = useCallback((next: DensityPreset) => {
    setPresetState(next);
    writePreset(next);
    document.documentElement.setAttribute("data-density", next);
  }, []);

  const cyclePreset = useCallback(() => {
    const order: DensityPreset[] = ["compact", "standard", "relaxed"];
    const idx = order.indexOf(preset);
    const next = order[(idx + 1) % order.length];
    setPreset(next);
  }, [preset, setPreset]);

  // Keyboard shortcut: 'd' to cycle (only when not typing)
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (
        e.key === "d" &&
        !e.metaKey &&
        !e.ctrlKey &&
        !e.altKey &&
        !(e.target instanceof HTMLInputElement) &&
        !(e.target instanceof HTMLTextAreaElement) &&
        !(e.target as HTMLElement).isContentEditable
      ) {
        e.preventDefault();
        cyclePreset();
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [cyclePreset]);

  // Apply density class to document on mount / change
  useEffect(() => {
    if (mounted) {
      document.documentElement.setAttribute("data-density", preset);
    }
  }, [preset, mounted]);

  return { preset, setPreset, cyclePreset, mounted };
}
