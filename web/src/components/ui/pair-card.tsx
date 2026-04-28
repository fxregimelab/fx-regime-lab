'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import type { Database } from '@/lib/supabase/database.types';
import { ConfidenceBar } from './confidence-bar';
import { fmt2, fmtInt } from './utils';

type PairMeta = { label: string; display: string; urlSlug: string; pairColor: string };
type RegimeCallRow = Pick<
  Database['public']['Tables']['regime_calls']['Row'],
  'regime' | 'confidence' | 'primary_driver'
>;
type SignalRow = Pick<
  Database['public']['Tables']['signals']['Row'],
  'spot' | 'day_change_pct' | 'rate_diff_2y' | 'cot_percentile' | 'realized_vol_20d'
>;

export function PairCard({
  pair,
  call,
  signals,
}: {
  pair: PairMeta;
  call?: RegimeCallRow | null;
  signals?: SignalRow | null;
}) {
  const router = useRouter();
  const pct = call ? Math.round(call.confidence * 100) : null;
  const chg = signals?.day_change_pct;

  return (
    <div
      onClick={() => router.push(`/terminal/fx-regime/${pair.urlSlug}`)}
      className="cursor-pointer transition-colors duration-150 p-5 bg-white hover:bg-[#fafafa] border border-[#e5e5e5] hover:border-[#888]"
      style={{ borderTop: `3px solid ${pair.pairColor}` }}
    >
      <div className="flex justify-between items-start mb-3">
        <div>
          <p className="font-sans font-bold text-[15px] text-[#0a0a0a] mb-0.5">{pair.display}</p>
          <p className="font-mono text-xl font-bold text-[#0a0a0a] tracking-tight tabular-nums">
            {signals?.spot?.toFixed(pair.label === 'USDJPY' ? 2 : 4) ?? '—'}
          </p>
        </div>
        {chg != null && (
          <span className={`font-mono text-xs font-semibold px-2 py-1 tabular-nums ${chg >= 0 ? 'text-[#16a34a] bg-[#f0fdf4]' : 'text-[#dc2626] bg-[#fff5f5]'}`}>
            {chg >= 0 ? '+' : ''}{chg.toFixed(2)}%
          </span>
        )}
      </div>

      <p className="font-mono text-[11px] font-bold text-[#111] tracking-wide leading-snug mb-3">
        {call?.regime ?? '—'}
      </p>
      <div className="mb-3">
        <span className="inline-block border border-[#dcdcdc] px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-[#666]">
          {call?.primary_driver ?? 'Mixed signals'}
        </span>
      </div>

      <div className="mb-3.5">
        <ConfidenceBar value={call?.confidence} tone="light" color={pair.pairColor} />
        <div className="flex justify-between mt-1.5">
          <span className="font-mono text-[9px] text-[#888] tracking-widest">CONFIDENCE</span>
          <span className="font-mono text-[11px] text-[#0a0a0a] font-bold tabular-nums">{pct != null ? `${pct}%` : '—'}</span>
        </div>
      </div>

      <div className="border-t border-[#f0f0f0] pt-3 flex flex-col gap-1.5">
        {[
          ['Rate diff 2Y', fmt2(signals?.rate_diff_2y)], 
          ['COT pctile', fmtInt(signals?.cot_percentile)], 
          ['Rvol 20d', fmt2(signals?.realized_vol_20d)]
        ].map(([lbl, val]) => (
          <div key={lbl} className="flex justify-between">
            <span className="font-mono text-[10px] text-[#888]">{lbl}</span>
            <span className="font-mono text-[11px] text-[#111] font-semibold tabular-nums">{val}</span>
          </div>
        ))}
      </div>

      <div className="mt-5">
        <div className="bg-[#0a0a0a] border border-[#333] text-white font-mono text-[10px] tracking-widest px-4 py-2 uppercase hover:bg-white hover:text-black transition-all w-full flex justify-between items-center rounded-none">
          <span>OPEN DESK</span>
          <span>→</span>
        </div>
      </div>
    </div>
  );
}
