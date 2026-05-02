'use client';

import { useState } from 'react';
import { ConnectDeskModal } from '@/components/ui/connect-desk-modal';

/** Terminal chrome: integrity log + connect desk entry (Obsidian glass, no radius). */
export function TerminalShellFooter() {
  const [deskOpen, setDeskOpen] = useState(false);

  return (
    <>
      <footer className="shrink-0 border-t border-solid border-[#111] bg-[#000000] px-4 py-2">
        <div className="flex flex-wrap items-center justify-between gap-2 font-mono text-[9px] tracking-widest text-[#666]">
          <a
            href="/audit"
            className="border border-solid border-[#222] bg-[#000000] px-2 py-1 text-[#888] no-underline hover:border-[#444] hover:text-[#ccc] rounded-none"
          >
            [ SYSTEM INTEGRITY LOG ]
          </a>
          <button
            type="button"
            onClick={() => setDeskOpen(true)}
            className="cursor-pointer border border-solid border-[#222] bg-[#000000] px-2 py-1 text-[#888] hover:border-[#444] hover:text-[#ccc] rounded-none"
          >
            [ CONNECT YOUR DESK ]
          </button>
        </div>
      </footer>
      <ConnectDeskModal open={deskOpen} onOpenChange={setDeskOpen} />
    </>
  );
}
