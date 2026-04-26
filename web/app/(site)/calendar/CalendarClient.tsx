'use client';

import { PAIRS } from '@/lib/mock/data';
import type { MacroEvent } from '@/lib/types';
import { useMemo, useState } from 'react';

type Filter = 'ALL' | 'EURUSD' | 'USDJPY' | 'USDINR';

function daysUntil(eventDate: string, anchor: string): number {
  const a = new Date(`${anchor}T12:00:00Z`).getTime();
  const e = new Date(`${eventDate}T12:00:00Z`).getTime();
  return Math.ceil((e - a) / 86400000);
}

function eventKey(e: MacroEvent): string {
  return `${e.date}-${e.event}`;
}

const pairDotClass: Record<string, string> = {
  EURUSD: 'bg-[#4BA3E3]',
  USDJPY: 'bg-[#F5923A]',
  USDINR: 'bg-[#D94030]',
};

function PairDots({ pairs }: { pairs: string[] }) {
  return (
    <span className="flex gap-1">
      {pairs.map((lbl) => (
        <span
          key={lbl}
          className={`inline-block h-[3px] w-[3px] rounded-full ${pairDotClass[lbl] ?? 'bg-[#ccc]'}`}
          aria-hidden
        />
      ))}
    </span>
  );
}

function impactClasses(impact: MacroEvent['impact']): string {
  if (impact === 'HIGH') return 'border border-[#dc2626] text-[#dc2626]';
  if (impact === 'MEDIUM') return 'border border-amber-500 text-amber-600';
  return 'border border-[#a0a0a0] text-[#a0a0a0]';
}

export function CalendarClient({
  events,
  anchorDate,
}: {
  events: MacroEvent[];
  anchorDate: string;
}) {
  const [filter, setFilter] = useState<Filter>('ALL');
  const [expanded, setExpanded] = useState<string | null>(null);

  const filtered = useMemo(() => {
    if (filter === 'ALL') return events;
    return events.filter((e) => e.pairs.includes(filter));
  }, [filter, events]);

  const bannerEvent = useMemo(() => {
    return filtered.find((e) => {
      if (e.impact !== 'HIGH') return false;
      const d = daysUntil(e.date, anchorDate);
      return d >= 0 && d <= 3;
    });
  }, [filtered, anchorDate]);

  const chips: { id: Filter; label: string }[] = [
    { id: 'ALL', label: 'ALL' },
    ...PAIRS.map((p) => ({ id: p.label, label: p.label })),
  ];

  return (
    <div>
      {bannerEvent ? (
        <div className="mb-10 bg-[#0a0a0a] px-5 py-4 text-[#e8e8e8]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="font-sans text-[14px] font-semibold">{bannerEvent.event}</p>
            <p className="font-mono text-[11px] text-[#bbb]">
              {daysUntil(bannerEvent.date, anchorDate)}d
            </p>
            <PairDots pairs={bannerEvent.pairs} />
          </div>
        </div>
      ) : null}

      <div className="mb-6 flex gap-2 overflow-x-auto pb-1">
        {chips.map((c) => (
          <button
            key={c.id}
            type="button"
            onClick={() => setFilter(c.id)}
            className={`shrink-0 rounded-full border px-3 py-1.5 font-mono text-[10px] ${
              filter === c.id
                ? 'border-[#0a0a0a] bg-[#0a0a0a] text-white'
                : 'border-[#e5e5e5] bg-white text-[#737373]'
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      <ul className="divide-y divide-[#e5e5e5] border-t border-[#e5e5e5]">
        {filtered.map((e) => {
          const key = eventKey(e);
          const open = expanded === key;
          return (
            <li key={key}>
              <button
                type="button"
                className="flex w-full flex-col gap-2 py-4 text-left sm:flex-row sm:items-center sm:gap-6"
                onClick={() => setExpanded(open ? null : key)}
              >
                <span className="w-24 shrink-0 font-mono text-[10px] text-[#737373]">{e.date}</span>
                <span className="min-w-0 flex-1 font-sans text-[14px] font-semibold text-[#0a0a0a]">
                  {e.event}
                </span>
                <span
                  className={`w-fit shrink-0 px-1.5 py-0.5 font-mono text-[8px] font-semibold uppercase ${impactClasses(e.impact)}`}
                >
                  {e.impact}
                </span>
                <PairDots pairs={e.pairs} />
              </button>
              {open ? (
                <pre className="mb-4 whitespace-pre-wrap border-l-2 border-[#e5e5e5] pl-4 font-mono text-[11px] leading-relaxed text-[#525252]">
                  {`${e.event} — pairs: ${e.pairs.join(', ')} · ${e.category}`}
                  {e.ai_brief ? `\n\n${e.ai_brief}` : '\n\nNo AI brief stored for this event yet.'}
                </pre>
              ) : null}
            </li>
          );
        })}
      </ul>

      <p className="mt-8 font-mono text-[10px] text-[#bbb]">
        High and medium impact events in the next 14 days (UTC).
      </p>
    </div>
  );
}
