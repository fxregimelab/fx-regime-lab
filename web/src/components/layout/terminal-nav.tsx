'use client';

import React, { useLayoutEffect, useMemo, useRef } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LogoMark } from '../ui/logo-mark';
import { PAIRS } from '@/lib/mockData';
import {
  useLatestSignals,
  useLatestRegimeCalls,
  useLastPipelineRun,
  useLatestDeskOpenCardsSnapshot,
  useLatestBrief,
} from '@/lib/queries';
import { MacroPulseBar, PULSE_BAR_H } from '../ui/macro-pulse-bar';
import { SystemicClusterBanner } from '../ui/systemic-cluster-banner';

// Row heights (px) — used to compute total sticky height for scroll offsets
const NAV_TOP_ROW_H = 38; // brand + status bar
const NAV_BOTTOM_ROW_H = 38; // breadcrumb + pair tabs
/** Minimum height before optional systemic + command rows (pulse + two nav rows). */
export const TERMINAL_NAV_MIN_H = PULSE_BAR_H + NAV_TOP_ROW_H + NAV_BOTTOM_ROW_H;
/** @deprecated Prefer CSS variable `--terminal-nav-h` (set by TerminalNav after layout). */
export const TERMINAL_NAV_H = TERMINAL_NAV_MIN_H;
const NAV_TOP_OFFSET = 32;
const COMMAND_STRIP_MIN_H = 56;

type PmTopItem = { label: string; prob: number | null };

function parsePolymarketTop3(raw: unknown): PmTopItem[] {
  if (!raw || typeof raw !== 'object') return [];
  const o = raw as Record<string, unknown>;
  const t3 = o.polymarket_top3;
  if (!Array.isArray(t3)) return [];
  return t3.slice(0, 3).map((item) => {
    if (!item || typeof item !== 'object') return { label: '', prob: null };
    const x = item as Record<string, unknown>;
    const p = x.prob;
    return {
      label: String(x.label ?? ''),
      prob: typeof p === 'number' && !Number.isNaN(p) ? p : null,
    };
  });
}

function formatPmProb(p: number | null): string {
  if (p == null) return '';
  const pct = p > 0 && p <= 1 ? p * 100 : p;
  return `${pct.toFixed(0)}%`;
}

export function TerminalNav() {
  const currentRoute = usePathname() || '';
  const pair = PAIRS.find((p) => currentRoute.includes(p.urlSlug));
  const headerRef = useRef<HTMLElement>(null);

  const signalsQ = useLatestSignals();
  const regimeQ = useLatestRegimeCalls();
  const lastRunQ = useLastPipelineRun();
  const deskSnapQ = useLatestDeskOpenCardsSnapshot();
  const latestBriefQ = useLatestBrief();

  const sortedDesk = useMemo(() => {
    const rows = deskSnapQ.data?.cards ?? [];
    return [...rows].sort((a, b) => (a.global_rank ?? 999) - (b.global_rank ?? 999));
  }, [deskSnapQ.data?.cards]);
  const rank1 = sortedDesk[0];
  const showSystemic = Boolean(
    rank1 &&
      rank1.telemetry_audit &&
      typeof rank1.telemetry_audit === 'object' &&
      (rank1.telemetry_audit as Record<string, unknown>).Systemic_Cluster,
  );
  const cmdBrief = latestBriefQ.data;
  const cmdPmTop = cmdBrief ? parsePolymarketTop3(cmdBrief.sentiment_json) : [];

  const { data: signals } = signalsQ;
  const err = signalsQ.isError || regimeQ.isError;
  const pending = signalsQ.isPending || regimeQ.isPending;

  useLayoutEffect(() => {
    const el = headerRef.current;
    if (!el) return;
    const h = el.offsetHeight;
    document.documentElement.style.setProperty('--terminal-nav-h', `${h}px`);
  }, [showSystemic, cmdBrief, deskSnapQ.data, pending, err]);

  const handleRefresh = () => {
    signalsQ.refetch();
    regimeQ.refetch();
    lastRunQ.refetch();
    deskSnapQ.refetch();
    latestBriefQ.refetch();
  };

  const asOfDay =
    lastRunQ.data?.slice(0, 10) ??
    (regimeQ.data?.EURUSD as { date?: string } | undefined)?.date ??
    new Date().toISOString().slice(0, 10);
  const utcClock = lastRunQ.data ? `${new Date(lastRunQ.data).toISOString().slice(11, 16)} UTC` : '—';

  return (
    <header
      ref={headerRef}
      className="border-b border-[#111] bg-[#000000] sticky z-[90] print:hidden overflow-hidden"
      style={{ top: `${NAV_TOP_OFFSET}px` }}
    >
      {/* Row 1 — Macro Pulse (fixed h-[28px]) */}
      <MacroPulseBar />

      {showSystemic ? <SystemicClusterBanner embedded /> : null}

      {cmdBrief ? (
        <div
          className="border-b border-[#222] bg-[#050505] px-4 sm:px-6 py-2.5 font-mono text-[10px] text-[#b0b0b0] tabular-nums tracking-wide max-w-[1152px] mx-auto w-full flex flex-col lg:flex-row lg:items-stretch lg:justify-between gap-3"
          style={{ minHeight: `${COMMAND_STRIP_MIN_H}px` }}
        >
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 min-w-0">
            <span className="text-[#777] tracking-widest">SYSTEMIC COMMAND</span>
            <span className="hidden sm:inline text-[#333]">|</span>
            <span>
              DOLLAR DOMINANCE:{' '}
              <span className="text-white tabular-nums">
                {cmdBrief.dollar_dominance == null ? '—' : `${cmdBrief.dollar_dominance.toFixed(1)}%`}
              </span>
            </span>
            <span className="text-[#333]">|</span>
            <span>
              OUTLIER:{' '}
              <span className="text-white tabular-nums">{cmdBrief.idiosyncratic_outlier || '—'}</span>
            </span>
          </div>
          <div className="lg:border-l lg:border-[#1a1a1a] lg:pl-4 min-w-[140px]">
            <p className="m-0 mb-1 text-[8px] tracking-widest text-[#555]">TOP POLYMARKET</p>
            <ul className="list-none m-0 p-0 flex flex-col gap-0.5 text-[9px] text-[#9a9a9a] tabular-nums">
              {cmdPmTop.length === 0 ? (
                <li>—</li>
              ) : (
                cmdPmTop.map((x, i) => (
                  <li key={i} className="truncate" title={x.label}>
                    {x.label.slice(0, 36)}
                    {x.prob != null ? `: ${formatPmProb(x.prob)}` : ''}
                  </li>
                ))
              )}
            </ul>
          </div>
        </div>
      ) : null}

      {/* Row 2 — Brand + status (fixed h-[38px]) */}
      <div
        className="border-b border-[#111] px-6 flex items-center justify-between max-w-[1152px] mx-auto h-[38px] overflow-hidden shrink-0"
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
              className={`w-1.5 h-1.5 shrink-0 ${err ? 'bg-[var(--color-bearish)]' : pending ? 'bg-[#737373]' : 'hidden'}`}
            />
            <span className={`font-mono text-[10px] ${err ? 'text-[var(--color-bearish)]' : 'text-[#737373]'}`}>
              {err ? 'ERROR' : pending ? 'LOADING' : 'SYNCED'} · {asOfDay} {utcClock}
            </span>
          </div>
        </div>
      </div>

      {/* Row 3 — Breadcrumb + pair tabs (fixed h-[38px]) */}
      <div
        className="max-w-[1152px] mx-auto px-6 flex items-center justify-between h-[38px] overflow-hidden shrink-0"
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
                  <span
                    className={`${chgPct >= 0 ? 'text-[var(--color-bullish)]' : 'text-[var(--color-bearish)]'}`}
                  >
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
