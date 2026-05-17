"use client";

import { useSyncUrlState } from "@/hooks/use-sync-url-state";
import { useEffect } from "react";

const DEFAULTS = {
  pair: "",
  regime: "",
  date: "",
};

/**
 * Reads URL params (?pair=eurusd&regime=Risk-On&date=2026-05-01)
 * on the FX Regime Mosaic and scrolls to / highlights the relevant pair.
 */
export function MosaicUrlSync() {
  const { state } = useSyncUrlState({ defaults: DEFAULTS });

  useEffect(() => {
    if (state.pair) {
      const slug = state.pair.toLowerCase();
      const el = document.getElementById(`mosaic-cell-${slug}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
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
