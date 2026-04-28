'use client';

import React from 'react';
import { useCrossAssetPulse } from '@/lib/queries';
import { fmt2, fmtChg } from './utils';

function PulseItem({ label, value, change, isPct = false }: { label: string; value: number | null; change: number | null; isPct?: boolean }) {
  const chg = fmtChg(change);
  return (
    <div className="flex items-baseline gap-2 shrink-0">
      <span className="font-mono text-[9px] text-[#666] tracking-widest">{label}</span>
      <span className="font-mono text-[11px] font-bold text-[#e8e8e8] tabular-nums">
        {value != null ? fmt2(value) + (isPct ? '%' : '') : '—'}
      </span>
      {change != null && (
        <span className="font-mono text-[10px] tabular-nums" style={{ color: chg.color }}>
          {chg.str}
        </span>
      )}
    </div>
  );
}

export function MacroPulseBar() {
  const { data, isPending } = useCrossAssetPulse();

  if (isPending || !data) {
    return (
      <div className="w-full bg-[#050505] border-b border-[#1a1a1a] py-1.5 px-6 flex items-center gap-6 overflow-x-auto hide-scrollbar z-50 min-h-[30px]">
        <div className="font-mono text-[9px] text-[#444] animate-pulse">SYNCING PULSE...</div>
      </div>
    );
  }

  return (
    <div className="w-full bg-[#050505] border-b border-[#1a1a1a] py-1.5 px-6 flex items-center gap-8 overflow-x-auto hide-scrollbar z-50 text-nowrap">
      <PulseItem label="DXY" value={data.dxy.value} change={data.dxy.change} />
      <div className="w-[1px] h-3 bg-[#1a1a1a]" />
      <PulseItem label="US10Y" value={data.us10y.value} change={data.us10y.change} isPct />
      <div className="w-[1px] h-3 bg-[#1a1a1a]" />
      <PulseItem label="VIX" value={data.vix.value} change={data.vix.change} />
      <div className="w-[1px] h-3 bg-[#1a1a1a]" />
      <PulseItem label="WTI" value={data.oil.value} change={data.oil.change} />
    </div>
  );
}
