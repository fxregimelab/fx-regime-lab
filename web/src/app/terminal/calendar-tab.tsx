'use client';

import { useState } from 'react';
import type { Database } from '@/lib/supabase/database.types';

type MacroEventRow = Database['public']['Tables']['macro_events']['Row'];

export function CalendarTab({
  events,
  todayIso,
  compact = false,
}: {
  events: MacroEventRow[];
  todayIso: string;
  compact?: boolean;
}) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const toggle = (k: string) => setExpanded((prev) => ({ ...prev, [k]: !prev[k] }));

  return (
    <div className="flex flex-col gap-3">
      {events.map((e) => {
        const isHigh = e.impact === 'HIGH';
        const days = Math.ceil((new Date(e.date).getTime() - new Date(todayIso).getTime()) / 86400000);
        const key = `${e.date}-${e.event}`;
        const hasAi = !!e.ai_brief;
        return (
          <div
            key={key}
            className={`border-l-2 pl-3 py-0.5 ${compact ? '' : 'pr-1'}`}
            style={{ borderColor: isHigh ? '#dc2626' : '#f59e0b' }}
          >
            <div className="flex justify-between items-baseline mb-1">
              <span className="font-mono text-[9px] text-[#888]">{e.date.slice(5)}</span>
              <span className={`font-mono text-[9px] ${days <= 2 ? 'text-[#fff]' : 'text-[#666]'}`}>
                {days === 0 ? 'TODAY' : days === 1 ? 'TOMORROW' : `${days}d`}
              </span>
            </div>
            <p className={`font-sans ${compact ? 'text-sm' : 'text-xs'} font-semibold text-[#ddd] leading-tight mb-1`}>
              {e.event}
            </p>
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-[8px] tracking-widest" style={{ color: isHigh ? '#dc2626' : '#f59e0b' }}>
                {e.impact}
              </span>
              {hasAi && (
                <button
                  type="button"
                  onClick={() => toggle(key)}
                  className="font-mono text-[8px] tracking-widest text-[#888] hover:text-[#bbb]"
                >
                  {expanded[key] ? 'HIDE AI' : 'SHOW AI'}
                </button>
              )}
            </div>
            {expanded[key] && hasAi && (
              <p className="mt-1.5 text-[10px] leading-relaxed text-[#9f9f9f] border border-[#1d1d1d] bg-[#111] p-2">
                {e.ai_brief}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
