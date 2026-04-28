'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LogoMark } from '../ui/logo-mark';
import { PAIRS } from '@/lib/mockData';
import { useLatestSignals, useLatestRegimeCalls, useLastPipelineRun } from '@/lib/queries';

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
    <header className="border-b border-[#1e1e1e] bg-[#080808] sticky top-0 z-50">
      <div className="border-b border-[#141414] px-6 h-[38px] flex items-center justify-between max-w-[1152px] mx-auto">
        <div className="flex items-center gap-2.5">
          <LogoMark size={16} />
          <span className="font-sans font-bold text-[13px] text-[#e8e8e8] tracking-tight">FX Regime Lab</span>
          <span className="font-mono text-[10px] text-[#333] ml-1">/ Terminal</span>
        </div>
        <div className="flex items-center gap-4">
          <button 
            onClick={handleRefresh}
            className="font-mono text-[9px] text-[#555] hover:text-[#888] transition-colors cursor-pointer border border-[#1a1a1a] px-1.5 py-0.5 bg-[#0a0a0a]"
            disabled={pending}
          >
            {pending ? 'SYNCING...' : 'REFRESH'}
          </button>
          <div className="flex items-center gap-1.5">
            <span
              className={`w-1.5 h-1.5 rounded-full shrink-0 ${err ? 'bg-[#f87171]' : pending ? 'bg-[#737373]' : 'live-indicator animate-pulse'}`}
            />
            <span className={`font-mono text-[10px] ${err ? 'text-[#f87171]' : 'text-[#888]'}`}>
              {err ? 'ERROR' : pending ? 'LOADING' : 'LIVE'} · {asOfDay} {utcClock}
            </span>
          </div>
        </div>
      </div>

      <div className="max-w-[1152px] mx-auto px-6 h-[38px] flex items-center justify-between">
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
                  <span className={`${chgPct >= 0 ? 'text-[#4ade80]' : 'text-[#f87171]'}`}>
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
