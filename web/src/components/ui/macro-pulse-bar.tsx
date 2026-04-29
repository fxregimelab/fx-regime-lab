'use client';

import React from 'react';
import { useCrossAssetPulse } from '@/lib/queries';
import { fmt2, fmtChg } from './utils';

// Exact bar height constant — import this in TerminalNav to offset sticky positioning
export const PULSE_BAR_H = 28; // px

function PulseItem({
  label,
  value,
  change,
  isPct = false,
}: {
  label: string;
  value: number | null;
  change: number | null;
  isPct?: boolean;
}) {
  const chg = fmtChg(change);
  return (
    <div className="flex items-baseline gap-1.5 shrink min-w-0">
      <span className="font-mono text-[9px] text-[#555] tracking-widest">{label}</span>
      <span className="font-mono text-[10px] font-bold text-[#e8e8e8] tabular-nums">
        {value != null ? fmt2(value) + (isPct ? '%' : '') : '—'}
      </span>
      {change != null && (
        <span className="font-mono text-[9px] tabular-nums" style={{ color: chg.color }}>
          {chg.str}
        </span>
      )}
    </div>
  );
}

const DIVIDER = <div className="w-[1px] h-2.5 bg-[#1a1a1a] shrink-0" />;

export function MacroPulseBar() {
  const { data, isPending } = useCrossAssetPulse();

  // Fixed height h-[28px] — never grows, never shifts
  return (
    <div
      className="w-full h-[28px] sticky top-0 z-[100] bg-[#000000] border-b border-[#111] flex items-center overflow-hidden whitespace-nowrap"
      style={{ height: `${PULSE_BAR_H}px` }}
    >
      {/* Scrolling marquee so content is never clipped and bar stays one line */}
      <div className="flex w-max min-w-full items-center gap-6 px-6 animate-pulse-marquee whitespace-nowrap">
        {isPending || !data ? (
          <span className="font-mono text-[9px] text-[#333] tracking-widest animate-pulse">
            SYNCING MACRO PULSE...
          </span>
        ) : (
          <>
            <PulseItem label="DXY" value={data.dxy.value} change={data.dxy.change} />
            {DIVIDER}
            <PulseItem label="US10Y" value={data.us10y.value} change={data.us10y.change} isPct />
            {DIVIDER}
            <PulseItem label="VIX" value={data.vix.value} change={data.vix.change} />
            {DIVIDER}
            <PulseItem label="WTI" value={data.oil.value} change={data.oil.change} />
            {/* Duplicate for seamless loop */}
            <span className="mx-6 text-[#1a1a1a] font-mono text-[9px]">·····</span>
            <PulseItem label="DXY" value={data.dxy.value} change={data.dxy.change} />
            {DIVIDER}
            <PulseItem label="US10Y" value={data.us10y.value} change={data.us10y.change} isPct />
            {DIVIDER}
            <PulseItem label="VIX" value={data.vix.value} change={data.vix.change} />
            {DIVIDER}
            <PulseItem label="WTI" value={data.oil.value} change={data.oil.change} />
          </>
        )}
      </div>
    </div>
  );
}
