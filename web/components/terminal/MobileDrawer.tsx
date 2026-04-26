'use client';

import type { MacroEvent, PairMeta } from '@/lib/types';
import { useState } from 'react';

import { AiTab } from './AiTab';
import { PairCalendarWidget } from './PairCalendarWidget';

export function MobileDrawer({
  pair,
  events,
  aiAnalysis,
  aiPrimaryDriver,
  aiFetchError,
}: {
  pair: PairMeta;
  events: MacroEvent[];
  aiAnalysis: string | null;
  aiPrimaryDriver: string | null;
  aiFetchError: string | null;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div
      className={`fixed bottom-0 left-0 right-0 z-50 border-t border-[#1e1e1e] bg-[#080808] lg:hidden ${
        open ? 'h-[60vh] max-h-[60vh]' : 'h-11'
      }`}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex h-11 w-full items-center justify-center font-mono text-[10px] text-[#555] hover:text-[#999]"
      >
        {open ? '▾ More' : '≡ More'}
      </button>
      {open ? (
        <div className="max-h-[calc(60vh-2.75rem)] overflow-y-auto border-t border-[#1e1e1e] p-3">
          <AiTab
            pair={pair}
            compact
            analysis={aiAnalysis}
            primaryDriver={aiPrimaryDriver}
            fetchError={aiFetchError}
          />
          <div className="mt-4 border-t border-[#1e1e1e] pt-4">
            <PairCalendarWidget pair={pair} events={events} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
