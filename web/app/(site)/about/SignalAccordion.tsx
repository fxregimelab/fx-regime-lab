'use client';

import { useState } from 'react';

const rows = [
  {
    id: 'rate',
    n: '01',
    color: 'text-[#4BA3E3]',
    title: 'Rate Differentials',
    summary: '2Y sovereign spreads anchor the structural USD read.',
    body: 'Policy divergence is expressed through the 2Y leg so the signal tracks near-term expectations instead of long bond term premia. Spreads feed the largest weight inside the composite.',
  },
  {
    id: 'cot',
    n: '02',
    color: 'text-[#F5923A]',
    title: 'COT Positioning',
    summary: 'Weekly speculative positioning as a crowding gauge.',
    body: 'Net non-commercial futures positions are rank-scored so extremes read consistently across pairs. Agreement with the rate leg lifts confidence; divergence tempers it.',
  },
  {
    id: 'vol',
    n: '03',
    color: 'text-[#D94030]',
    title: 'Realized Volatility',
    summary: 'Short and medium realized vol vs implied for a vol-tax check.',
    body: 'Five- and twenty-day realized paths are stacked against 30-day implied to see whether options markets are charging for risk that spot has not yet printed.',
  },
  {
    id: 'oi',
    n: '04',
    color: 'text-[#888888]',
    title: 'OI and Risk Reversals',
    summary: 'Skew and open interest for asymmetric positioning.',
    body: '25-delta risk reversals highlight directional hedging demand while OI changes flag whether leverage is building into a move. INR includes additional domestic series.',
  },
] as const;

export function SignalAccordion() {
  const [open, setOpen] = useState<string | null>('rate');
  return (
    <div className="divide-y divide-[#e5e5e5] border border-[#e5e5e5]">
      {rows.map((r) => {
        const isOpen = open === r.id;
        return (
          <div key={r.id}>
            <button
              type="button"
              className="flex w-full items-start gap-4 px-4 py-4 text-left"
              onClick={() => setOpen(isOpen ? null : r.id)}
            >
              <span className={`font-mono text-[11px] font-bold ${r.color}`}>{r.n}</span>
              <span className="flex-1">
                <span className="font-sans text-[14px] font-semibold text-[#0a0a0a]">
                  {r.title}
                </span>
                <span className="mt-1 block font-sans text-[13px] text-[#737373]">{r.summary}</span>
              </span>
            </button>
            {isOpen ? (
              <div className="border-t border-[#f0f0f0] px-4 pb-4 pl-[52px] pt-2">
                <p className="font-sans text-[13px] leading-relaxed text-[#525252]">{r.body}</p>
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
