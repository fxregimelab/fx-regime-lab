'use client';

import type { ReactNode } from 'react';
import { TerminalContextRail } from '@/components/layout/terminal-context-rail';
import { TerminalMobileBottomNav } from '@/components/layout/terminal-mobile-bottom-nav';
import { TerminalShellFooter } from '@/components/layout/terminal-shell-footer';
import { TerminalNav } from '@/components/layout/terminal-nav';

/** Persistent G10 terminal chrome: context rail, macro pulse, optional systemic banner, command strip, pair nav. */
export default function TerminalLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <div className="flex h-[100dvh] w-screen max-w-[100vw] overflow-hidden bg-[#000000]">
        <div className="relative hidden md:block w-[54px] shrink-0 self-stretch min-h-0 h-full">
          <TerminalContextRail />
        </div>
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden pb-16 md:pb-0">
          <TerminalNav />
          <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden">{children}</div>
          <TerminalShellFooter />
        </div>
      </div>
      <TerminalMobileBottomNav />
    </>
  );
}
