import type { MacroEvent, PairMeta } from '@/lib/types';

import { AiTab } from './AiTab';
import { PairCalendarWidget } from './PairCalendarWidget';

export function TerminalSidebar({
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
  return (
    <aside
      className="hidden w-[320px] min-h-full shrink-0 border-l border-[#1e1e1e] bg-[#0c0c0c] p-4 lg:block"
      aria-label="Context"
    >
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
    </aside>
  );
}
