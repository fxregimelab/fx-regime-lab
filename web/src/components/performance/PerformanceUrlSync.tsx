"use client";

import { useSyncUrlState } from "@/hooks/use-sync-url-state";
import { useEffect } from "react";

const DEFAULTS = {
  pair: "",
  window: "",
};

/**
 * Reads URL params (?pair=eurusd&window=90d) on the performance page
 * and scrolls to / highlights the relevant section.
 */
export function PerformanceUrlSync() {
  const { state } = useSyncUrlState({ defaults: DEFAULTS });

  useEffect(() => {
    if (state.pair) {
      const el = document.getElementById(
        `pair-section-${state.pair.toLowerCase()}`,
      );
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        el.classList.add("ring-1", "ring-[var(--color-warn)]");
        setTimeout(
          () => el.classList.remove("ring-1", "ring-[var(--color-warn)]"),
          3000,
        );
      }
    }
  }, [state.pair]);

  return null;
}
