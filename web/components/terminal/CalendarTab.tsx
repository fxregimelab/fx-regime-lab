import type { MacroEvent, PairMeta } from '@/lib/types';

import { impactText } from './PairCalendarWidget';
import { TerminalEmptyState } from './TerminalEmptyState';

function filterEvents(events: MacroEvent[], pairLabel: string) {
  return events
    .filter((e) => e.pairs.includes(pairLabel))
    .sort((a, b) => a.date.localeCompare(b.date));
}

export function CalendarTab({ pair, events }: { pair: PairMeta; events: MacroEvent[] }) {
  const list = filterEvents(events, pair.label);
  if (list.length === 0) {
    return <TerminalEmptyState message="No upcoming events for this pair" />;
  }
  return (
    <ul className="space-y-3">
      {list.map((e) => (
        <li key={`${e.date}-${e.event}`} className="border-b border-[#1e1e1e] pb-3 last:border-b-0">
          <p className="font-mono text-[9px] text-[#555]">{e.date}</p>
          <div className="mt-1 flex flex-wrap items-baseline justify-between gap-2">
            <p className="font-sans text-[13px] font-semibold text-[#e8e8e8]">{e.event}</p>
            <span
              className={`shrink-0 border border-[#1e1e1e] px-1 font-mono text-[8px] ${impactText[e.impact]}`}
            >
              {e.impact}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}

/** Alias for spec / imports */
export { CalendarTab as PairCalendarTab };
