"use client";

import { KeyboardHelp } from "@/components/ui/keyboard-help";
import { useVimNav } from "@/hooks/use-vim-nav";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

const PAIR_PATHS = [
  "/terminal/fx-regime/eurusd",
  "/terminal/fx-regime/usdjpy",
  "/terminal/fx-regime/usdinr",
];

/**
 * Vim-style keyboard navigation for terminal pages.
 * j/k: scroll, g: goto pair, /: search, ?: help, r: refresh, 1/2/3: switch pair
 */
export function VimNavProvider() {
  const router = useRouter();

  const refresh = useCallback(() => {
    router.refresh();
  }, [router]);

  const gotoPair = useCallback(() => {
    // Dispatch custom event that CommandPalette listens for
    document.dispatchEvent(
      new CustomEvent("fxrl:open-command-palette", {
        detail: { filter: "pair" },
      }),
    );
  }, []);

  const openSearch = useCallback(() => {
    document.dispatchEvent(
      new CustomEvent("fxrl:open-command-palette", {
        detail: { filter: "search" },
      }),
    );
  }, []);

  const { helpOpen, setHelpOpen } = useVimNav({
    enabled: true,
    actions: {
      scrollDown: () =>
        window.scrollBy({ top: window.innerHeight * 0.5, behavior: "smooth" }),
      scrollUp: () =>
        window.scrollBy({ top: -window.innerHeight * 0.5, behavior: "smooth" }),
      refresh,
      gotoPair,
      openSearch,
      switchPair: (idx: number) => router.push(PAIR_PATHS[idx]),
    },
    pairPaths: PAIR_PATHS,
  });

  return <KeyboardHelp open={helpOpen} onClose={() => setHelpOpen(false)} />;
}
