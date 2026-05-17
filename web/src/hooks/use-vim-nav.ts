"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

export interface VimNavActions {
  /** Scroll down by one viewport chunk. */
  scrollDown: () => void;
  /** Scroll up by one viewport chunk. */
  scrollUp: () => void;
  /** Refresh the current page data. */
  refresh: () => void;
  /** Open command palette filtered to pairs. */
  gotoPair: () => void;
  /** Open command palette for search. */
  openSearch: () => void;
  /** Navigate to a specific pair index (1, 2, 3). */
  switchPair: (index: number) => void;
}

interface UseVimNavOptions {
  /** Whether vim nav is active. Default: true on terminal pages. */
  enabled?: boolean;
  /** Callbacks for actions. */
  actions: VimNavActions;
  /** Available pair paths for 1/2/3 switching. */
  pairPaths?: string[];
}

/**
 * Vim-style keyboard navigation for terminal pages.
 *
 * j/k: scroll down/up
 * g:   goto pair (opens command palette filtered to pairs)
 * /:   search (opens command palette)
 * ?:   show keyboard shortcuts help overlay
 * r:   refresh data
 * 1/2/3: switch to pair 1/2/3
 */
export function useVimNav({
  enabled = true,
  actions,
  pairPaths = [
    "/terminal/fx-regime/eurusd",
    "/terminal/fx-regime/usdjpy",
    "/terminal/fx-regime/usdinr",
  ],
}: UseVimNavOptions) {
  const [helpOpen, setHelpOpen] = useState(false);
  const router = useRouter();

  const scrollDown = useCallback(() => {
    window.scrollBy({ top: window.innerHeight * 0.5, behavior: "smooth" });
  }, []);

  const scrollUp = useCallback(() => {
    window.scrollBy({ top: -window.innerHeight * 0.5, behavior: "smooth" });
  }, []);

  useEffect(() => {
    if (!enabled) return;

    const down = (e: KeyboardEvent) => {
      // Ignore if user is typing in an input/textarea
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        return;
      }

      // Ignore if modifiers are pressed (except for ? which uses Shift)
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      switch (e.key) {
        case "j":
          e.preventDefault();
          actions.scrollDown?.() ?? scrollDown();
          break;
        case "k":
          e.preventDefault();
          actions.scrollUp?.() ?? scrollUp();
          break;
        case "g":
          e.preventDefault();
          actions.gotoPair();
          break;
        case "/":
          e.preventDefault();
          actions.openSearch();
          break;
        case "?":
          e.preventDefault();
          setHelpOpen(true);
          break;
        case "r":
        case "R":
          e.preventDefault();
          actions.refresh();
          break;
        case "1":
          e.preventDefault();
          if (pairPaths[0]) {
            actions.switchPair?.(0) ?? router.push(pairPaths[0]);
          }
          break;
        case "2":
          e.preventDefault();
          if (pairPaths[1]) {
            actions.switchPair?.(1) ?? router.push(pairPaths[1]);
          }
          break;
        case "3":
          e.preventDefault();
          if (pairPaths[2]) {
            actions.switchPair?.(2) ?? router.push(pairPaths[2]);
          }
          break;
        default:
          break;
      }
    };

    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [enabled, actions, pairPaths, router, scrollDown, scrollUp]);

  return { helpOpen, setHelpOpen };
}
