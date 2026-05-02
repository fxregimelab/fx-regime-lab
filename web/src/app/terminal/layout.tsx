'use client';

import type { ReactNode } from 'react';
import { TerminalContextRail } from '@/components/layout/terminal-context-rail';
import { TerminalShellFooter } from '@/components/layout/terminal-shell-footer';
import { TerminalNav } from '@/components/layout/terminal-nav';

/** Persistent G10 terminal chrome: context rail, macro pulse, optional systemic banner, command strip, pair nav. */
export default function TerminalLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-[#000000]">
      <div className="relative w-[54px] shrink-0 self-stretch min-h-screen">
        <TerminalContextRail />
      </div>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <TerminalNav />
        <div className="min-h-0 flex-1 overflow-auto">{children}</div>
        <TerminalShellFooter />
      </div>
    </div>
  );
}
