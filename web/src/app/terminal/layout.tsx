'use client';

import type { ReactNode } from 'react';
import { GlobalHeatmapStrip } from '@/components/layout/global-heatmap-strip';
import { TerminalContextRail } from '@/components/layout/terminal-context-rail';
import { TerminalMobileBottomNav } from '@/components/layout/terminal-mobile-bottom-nav';
import { TerminalPairCarouselMobile } from '@/components/layout/terminal-pair-carousel-mobile';
import { TerminalRouteTransition } from '@/components/layout/terminal-route-transition';
import { TerminalShellFooter } from '@/components/layout/terminal-shell-footer';
import { TerminalNav } from '@/components/layout/terminal-nav';
import { useLocalSettings } from '@/hooks/useLocalSettings';
import { motion } from 'framer-motion';

/** Persistent G10 terminal chrome: context rail, optional systemic banner, command strip, pair nav. */
export default function TerminalLayout({ children }: { children: ReactNode }) {
  const { sidebarExpanded } = useLocalSettings();

  return (
    <div
      data-fxrl-terminal
      className="flex h-full min-h-0 w-screen max-w-[100vw] overflow-hidden flex-col bg-[var(--bg-void)]"
    >
      <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden">
        <motion.div 
          initial={false}
          animate={{ width: sidebarExpanded ? 160 : 54 }}
          transition={{ duration: 0.22, ease: [0.25, 0.1, 0.25, 1] }}
          className="relative hidden md:block shrink-0 self-stretch min-h-0 h-full"
        >
          <TerminalContextRail />
        </motion.div>
        <GlobalHeatmapStrip />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden pb-16 md:pb-0">
          <TerminalNav />
          <TerminalPairCarouselMobile />
          <TerminalRouteTransition>{children}</TerminalRouteTransition>
          <TerminalShellFooter />
        </div>
      </div>
      <TerminalMobileBottomNav />
    </div>
  );
}
