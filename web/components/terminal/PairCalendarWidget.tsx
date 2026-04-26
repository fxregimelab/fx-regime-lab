import type { MacroEvent, PairMeta } from '@/lib/types';

const impactText: Record<string, string> = {
  HIGH: 'text-[#ef4444]',
  MEDIUM: 'text-[#f59e0b]',
  LOW: 'text-[#555]',
};

function filterUpcoming(events: MacroEvent[], pairLabel: string, limit: number) {
  return events
    .filter((e) => e.pairs.includes(pairLabel))
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(0, limit);
}

export function PairCalendarWidget({ pair, events }: { pair: PairMeta; events: MacroEvent[] }) {
  const next = filterUpcoming(events, pair.label, 3);
  return (
    <div>
      <p className="font-mono text-[8px] font-normal tracking-widest text-[#555]">UPCOMING</p>
      {next.length === 0 ? (
        <p className="mt-2 font-sans text-[12px] text-[#555]">No events</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {next.map((e) => (
            <li
              key={`${e.date}-${e.event}`}
              className="border-b border-[#1e1e1e] pb-2 last:border-b-0"
            >
              <p className="font-mono text-[8px] text-[#555]">{e.date}</p>
              <p className="mt-0.5 font-sans text-[12px] font-semibold leading-snug text-[#e8e8e8]">
                {e.event}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export { impactText };
