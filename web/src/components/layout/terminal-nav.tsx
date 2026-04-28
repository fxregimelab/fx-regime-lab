'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LogoMark } from '../ui/logo-mark';
import { PAIRS } from '@/lib/mockData';
import { useLatestSignals, useLatestRegimeCalls, useLastPipelineRun } from '@/lib/queries';
import { MacroPulseBar, PULSE_BAR_H } from '../ui/macro-pulse-bar';

// Row heights (px) — used to compute total sticky height for scroll offsets
const NAV_TOP_ROW_H = 38; // brand + status bar
const NAV_BOTTOM_ROW_H = 38; // breadcrumb + pair tabs
export const TERMINAL_NAV_H = PULSE_BAR_H + NAV_TOP_ROW_H + NAV_BOTTOM_ROW_H; // 104px total
const NAV_TOP_OFFSET = 32;

export function TerminalNav() {
  const currentRoute = usePathname() || '';
  const pair = PAIRS.find((p) => currentRoute.includes(p.urlSlug));

  const signalsQ = useLatestSignals();
  const regimeQ = useLatestRegimeCalls();
  const lastRunQ = useLastPipelineRun();

  const { data: signals } = signalsQ;
  const err = signalsQ.isError || regimeQ.isError;
  const pending = signalsQ.isPending || regimeQ.isPending;

  const handleRefresh = () => {
    signalsQ.refetch();
    regimeQ.refetch();
    lastRunQ.refetch();
  };

  const asOfDay =
    lastRunQ.data?.slice(0, 10) ??
    (regimeQ.data?.EURUSD as { date?: string } | undefined)?.date ??
    new Date().toISOString().slice(0, 10);
  const utcClock = lastRunQ.data ? `${new Date(lastRunQ.data).toISOString().slice(11, 16)} UTC` : '—';

  return (
    <header
      className="border-b border-[#111] bg-[#000000] sticky z-[90] print:hidden"
      style={{ minHeight: `${TERMINAL_NAV_H}px`, top: `${NAV_TOP_OFFSET}px` }}
    >
      {/* Row 1 — Macro Pulse (fixed h-[28px]) */}
      <MacroPulseBar />

      {/* Row 2 — Brand + status (fixed h-[38px]) */}
      <div
        className="border-b border-[#111] px-6 flex items-center justify-between max-w-[1152px] mx-auto"
        style={{ height: `${NAV_TOP_ROW_H}px` }}
      >
        <div className="flex items-center gap-2.5">
          <LogoMark size={24} />
          <span className="font-mono text-[10px] text-[#333]">/ Terminal</span>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={handleRefresh}
            className="font-mono text-[9px] text-[#555] hover:text-[#888] transition-colors cursor-pointer border border-[#111] px-1.5 py-0.5 bg-[#000000]"
            disabled={pending}
          >
            {pending ? 'SYNCING...' : 'REFRESH'}
          </button>
          <div className="flex items-center gap-1.5">
            <span
              className={`w-1.5 h-1.5 shrink-0 ${err ? 'bg-[#ef4444]' : pending ? 'bg-[#737373]' : 'hidden'}`}
            />
            <span className={`font-mono text-[10px] ${err ? 'text-[#ef4444]' : 'text-[#737373]'}`}>
              {err ? 'ERROR' : pending ? 'LOADING' : 'SYNCED'} · {asOfDay} {utcClock}
            </span>
          </div>
        </div>
      </div>

      {/* Row 3 — Breadcrumb + pair tabs (fixed h-[38px]) */}
      <div
        className="max-w-[1152px] mx-auto px-6 flex items-center justify-between"
        style={{ height: `${NAV_BOTTOM_ROW_H}px` }}
      >
        <div className="flex items-center gap-1.5 font-mono text-[10px]">
          <Link href="/" className="text-[#888] hover:text-[#aaa] transition-colors">
            shell
          </Link>
          <span className="text-[#555]">/</span>
          <Link href="/terminal" className={`${currentRoute === '/terminal' ? 'text-[#ddd]' : 'text-[#777]'}`}>
            terminal
          </Link>
          {currentRoute.includes('/fx-regime') && (
            <>
              <span className="text-[#555]">/</span>
              <Link
                href="/terminal/fx-regime"
                className={`${currentRoute === '/terminal/fx-regime' ? 'text-[#ddd]' : 'text-[#777]'}`}
              >
                fx-regime
              </Link>
            </>
          )}
          {pair && (
            <>
              <span className="text-[#555]">/</span>
              <span className="font-semibold" style={{ color: pair.pairColor }}>
                {pair.urlSlug}
              </span>
            </>
          )}
        </div>

        <div className="flex gap-0.5">
          {PAIRS.map((p) => {
            const active = currentRoute.includes(p.urlSlug);
            const sig = signals?.[p.label];
            const chgPct = sig?.day_change_pct as number | undefined;
            return (
              <Link
                key={p.label}
                href={`/terminal/fx-regime/${p.urlSlug}`}
                className="flex items-center gap-2 px-3 py-1 font-mono text-[10px] border-b-2 transition-all -mb-[1px]"
                style={{
                  background: active ? '#141414' : 'transparent',
                  borderBottomColor: active ? p.pairColor : 'transparent',
                }}
              >
                <span className="font-bold" style={{ color: p.pairColor }}>
                  {p.display}
                </span>
                {sig && chgPct != null && (
                  <span className={`${chgPct >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
                    {chgPct >= 0 ? '+' : ''}
                    {chgPct.toFixed(2)}%
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      </div>
    </header>
  );
}
