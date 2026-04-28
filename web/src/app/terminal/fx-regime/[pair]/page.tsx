'use client';

import React, { useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { TerminalNav } from '@/components/layout/terminal-nav';
import { PAIRS } from '@/lib/mockData';
import { fmt2, fmtInt, fmtPct, fmtChg } from '@/components/ui/utils';
import { ConfidenceBar } from '@/components/ui/confidence-bar';
import { motion } from 'framer-motion';
import dynamic from 'next/dynamic';
import { Sparkline } from '@/components/ui/sparkline';
import { ClickToCopy } from '@/components/ui/click-to-copy';
import { Menu, X } from 'lucide-react';
import {
  useLatestRegimeCalls,
  useLatestSignals,
  useRegimeHistory,
  useRegimeHistory30D,
  useUpcomingMacroEvents,
  usePairBrief,
  useSignalHistory,
  useLastPipelineRun,
  sparkNumericSeries,
  useCrossAssetPulse,
} from '@/lib/queries';
import { CalendarTab } from '@/app/terminal/calendar-tab';
import type { Database } from '@/lib/supabase/database.types';
import { MethodologyPopover } from '@/components/ui/methodology-popover';

const ClientChart = dynamic(() => import('@/components/ui/client-chart'), {
  ssr: false,
  loading: () => <p className="font-mono text-[11px] text-[#444] z-10">[ Loading Chart... ]</p>,
});

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } };
const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.2, ease: 'easeOut' as const } },
};

const SidebarRawTelemetry = React.memo(function SidebarRawTelemetry({
  cotNet, vol5d, vol20d, oiDelta, pairChg
}: {
  cotNet?: number, vol5d?: number, vol20d?: number, oiDelta?: number, pairChg?: number
}) {
  const pulseQ = useCrossAssetPulse();
  const dxyChg = pulseQ.data?.dxy.change ?? undefined;
  const oilChg = pulseQ.data?.oil.change ?? undefined;

  const getCorrStr = (p?: number, a?: number) => {
    if (p == null || a == null) return '—';
    if ((p >= 0 && a >= 0) || (p < 0 && a < 0)) return 'POSITIVE (1D)';
    return 'INVERSE (1D)';
  };

  const getCorrColor = (str: string) => {
    if (str === 'POSITIVE (1D)') return 'text-[#22c55e]';
    if (str === 'INVERSE (1D)') return 'text-[#ef4444]';
    return 'text-[#737373]';
  };

  const dxyCorr = getCorrStr(pairChg, dxyChg);
  const oilCorr = getCorrStr(pairChg, oilChg);

  return (
    <div className="p-4 border-b border-[#141414]">
      <p className="font-mono text-[9px] text-[#666] tracking-widest mb-4">[ RAW TELEMETRY ]</p>
      <div className="space-y-4">
        <div>
          <p className="font-mono text-[9px] text-[#555] tracking-widest mb-1.5 flex items-center">COT NET POSITION <MethodologyPopover metricKey="cot" /></p>
          <p className="font-mono text-[10px] text-[#e8e8e8] tabular-nums">
            {fmtInt(cotNet)}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <p className="font-mono text-[9px] text-[#555] tracking-widest mb-1.5 flex items-center">5D VOL <MethodologyPopover metricKey="realizedVol" /></p>
            <p className="font-mono text-[10px] text-[#e8e8e8] tabular-nums">
              {fmt2(vol5d)}%
            </p>
          </div>
          <div>
            <p className="font-mono text-[9px] text-[#555] tracking-widest mb-1.5 flex items-center">20D VOL <MethodologyPopover metricKey="realizedVol" /></p>
            <p className="font-mono text-[10px] text-[#e8e8e8] tabular-nums">
              {fmt2(vol20d)}%
            </p>
          </div>
        </div>
        <div>
          <p className="font-mono text-[9px] text-[#555] tracking-widest mb-1.5">OPEN INTEREST CHG</p>
          <p className="font-mono text-[10px] text-[#e8e8e8] tabular-nums">
            {fmt2(oiDelta)}
          </p>
        </div>
      </div>
      
      <div className="mt-6 border-t border-[#1a1a1a] pt-4">
        <p className="font-mono text-[9px] text-[#666] tracking-widest mb-3">[ CORRELATION MATRIX ]</p>
        <div className="space-y-2">
          <div className="flex justify-between">
            <span className="font-mono text-[10px] text-[#888]">vs DXY</span>
            <span className={`font-mono text-[10px] tabular-nums ${getCorrColor(dxyCorr)}`}>{dxyCorr}</span>
          </div>
          <div className="flex justify-between">
            <span className="font-mono text-[10px] text-[#888]">vs WTI (CL=F)</span>
            <span className={`font-mono text-[10px] tabular-nums ${getCorrColor(oilCorr)}`}>{oilCorr}</span>
          </div>
        </div>
      </div>
    </div>
  );
});

type MacroEventRow = Database['public']['Tables']['macro_events']['Row'];

export default function PairDeskPage() {
  const params = useParams();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [focusMode, setFocusMode] = useState(false);
  const pairSlug = params.pair as string;
  const pair = PAIRS.find((p) => p.urlSlug === pairSlug) ?? PAIRS[0];

  // [F] keyboard shortcut toggles focus mode
  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'f' || e.key === 'F') {
        if ((e.target as HTMLElement).tagName === 'INPUT') return;
        setFocusMode((v) => !v);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const handlePrint = () => window.print();

  const regimeQ = useLatestRegimeCalls();
  const signalsQ = useLatestSignals();
  const historyQ = useRegimeHistory(pair.label);
  const regime30Q = useRegimeHistory30D(pair.label);
  const eventsQ = useUpcomingMacroEvents();
  const briefQ = usePairBrief(pair.label);
  const sigHistQ = useSignalHistory(pair.label, 30);
  const lastRunQ = useLastPipelineRun();

  const call = regimeQ.data?.[pair.label];
  const sig = signalsQ.data?.[pair.label];
  const history = (historyQ.data ?? []) as { date: string; regime: string; confidence: number }[];
  const mainErr = regimeQ.isError || signalsQ.isError;

  const rateSpark = useMemo(() => {
    const rows = (sigHistQ.data ?? []) as { rate_diff_2y?: number | null }[];
    return sparkNumericSeries(
      rows.map((r) => Number(r.rate_diff_2y ?? 0)),
      7,
    );
  }, [sigHistQ.data]);

  const volSpark = useMemo(() => {
    const rows = (sigHistQ.data ?? []) as { realized_vol_20d?: number | null }[];
    return sparkNumericSeries(
      rows.map((r) => Number(r.realized_vol_20d ?? 0)),
      7,
    );
  }, [sigHistQ.data]);

  const cotSpark = useMemo(() => {
    const rows = (sigHistQ.data ?? []) as { cot_percentile?: number | null }[];
    return sparkNumericSeries(
      rows.map((r) => Number(r.cot_percentile ?? 0)),
      7,
    );
  }, [sigHistQ.data]);

  const events: MacroEventRow[] = (eventsQ.data ?? [])
    .filter((e) => !e.pairs?.length || e.pairs.includes(pair.label))
    .slice(0, 5);

  const sigHist = sigHistQ.data ?? [];
  const latestSigForTrend = sigHist[sigHist.length - 1];
  const prevSigForTrend = sigHist[sigHist.length - 2];
  let isSteepening = false;
  let curveTrendStr = '—';
  if (latestSigForTrend && prevSigForTrend && latestSigForTrend.rate_diff_10y != null && latestSigForTrend.rate_diff_2y != null && prevSigForTrend.rate_diff_10y != null && prevSigForTrend.rate_diff_2y != null) {
    const curveLatest = latestSigForTrend.rate_diff_10y - latestSigForTrend.rate_diff_2y;
    const curvePrev = prevSigForTrend.rate_diff_10y - prevSigForTrend.rate_diff_2y;
    isSteepening = curveLatest > curvePrev;
    curveTrendStr = isSteepening ? '↑ STEEP' : '↓ FLAT';
  }

  const chgObj = fmtChg(sig?.day_change_pct as number | undefined);

  const TODAY =
    lastRunQ.data?.slice(0, 10) ??
    (call as { date?: string } | undefined)?.date ??
    new Date().toISOString().slice(0, 10);

  const analysisText = (briefQ.data?.analysis as string | null) ?? '';
  const paragraphs = analysisText ? analysisText.split(/\n\n+/).filter(Boolean) : [];

  // Regime Shift Log — find last 3 regime transitions
  const regimeShiftLog = useMemo(() => {
    const h = (historyQ.data ?? []) as { date: string; regime: string; confidence: number }[];
    if (h.length < 2) return [];
    const shifts: { fromRegime: string; toRegime: string; date: string; durationDays: number }[] = [];
    for (let i = 1; i < h.length; i++) {
      if (h[i].regime !== h[i - 1].regime) {
        // Duration = days from this shift to the previous one (or to the start)
        const prevShiftIdx = shifts.length > 0 ? h.findIndex((x) => x.date === shifts[shifts.length - 1].date) : 0;
        const durationDays = i - prevShiftIdx;
        shifts.push({
          fromRegime: h[i - 1].regime,
          toRegime: h[i].regime,
          date: h[i].date,
          durationDays,
        });
        if (shifts.length === 3) break;
      }
    }
    return shifts;
  }, [historyQ.data]);

  return (
    <div className="min-h-screen flex flex-col bg-[#050505] text-[#e8e8e8] relative" data-focus={focusMode ? '1' : '0'}>
      {/* Print-only research brief overlay */}
      <div className="hidden print:block fixed inset-0 bg-white text-[#0a0a0a] z-[9999] p-12 overflow-auto">
        <div className="max-w-[800px] mx-auto">
          <div className="flex justify-between items-start border-b border-[#ddd] pb-6 mb-8">
            <div>
              <h1 className="text-2xl font-bold tracking-tight mb-1">{pair.display} — Research Brief</h1>
              <p className="text-sm text-[#666] font-mono">GENERATED: {TODAY} · FX Regime Lab</p>
            </div>
            <div className="text-right">
              <p className="font-mono text-xs text-[#666]">ACTIVE REGIME</p>
              <p className="font-mono text-lg font-bold">{(call?.regime as string) ?? '—'}</p>
              <p className="font-mono text-sm text-[#666]">Conf: {fmtPct(call?.confidence as number | undefined)}</p>
            </div>
          </div>
          <div className="grid grid-cols-4 border border-[#ddd] mb-8">
            {[{ label: 'RATES', sig: call?.rate_signal },{ label: 'COT', sig: call?.cot_signal },{ label: 'VOL', sig: call?.vol_signal },{ label: 'OI', sig: call?.oi_signal }].map(s => (
              <div key={s.label} className="p-4 border-r border-[#ddd] last:border-r-0 text-center">
                <p className="text-xs font-mono text-[#666] mb-2">{s.label}</p>
                <p className={`text-sm font-bold font-mono ${s.sig === 'BULLISH' ? 'text-green-600' : s.sig === 'BEARISH' ? 'text-red-600' : 'text-[#666]'}`}>{(s.sig as string) ?? 'NEUTRAL'}</p>
              </div>
            ))}
          </div>
          <div className="mb-8">
            <p className="text-xs font-mono text-[#666] mb-3 uppercase tracking-widest border-b border-[#ddd] pb-2">Signal Composite · {fmt2(call?.signal_composite as number | undefined)}</p>
            <div className="grid grid-cols-3 gap-6 text-sm">
              <div><p className="text-xs text-[#666] font-mono mb-1">2Y SPREAD</p><p className="font-mono font-bold">{fmt2(sig?.rate_diff_2y as number | undefined)}</p></div>
              <div><p className="text-xs text-[#666] font-mono mb-1">REALIZED VOL (20D)</p><p className="font-mono font-bold">{fmt2(sig?.realized_vol_20d as number | undefined)}%</p></div>
              <div><p className="text-xs text-[#666] font-mono mb-1">COT PERCENTILE</p><p className="font-mono font-bold">{fmtInt(sig?.cot_percentile as number | undefined)}</p></div>
            </div>
          </div>
          <div className="mb-8">
            <p className="text-xs font-mono text-[#666] mb-3 uppercase tracking-widest border-b border-[#ddd] pb-2">AI Analysis</p>
            <p className="text-sm leading-relaxed text-[#333]">{analysisText || 'No AI analysis available for this cycle.'}</p>
          </div>
          <div>
            <p className="text-xs font-mono text-[#666] mb-3 uppercase tracking-widest border-b border-[#ddd] pb-2">Macro Pulse (Cross-Asset)</p>
            <div className="grid grid-cols-4 gap-4 text-sm">
              <div><p className="text-xs text-[#666] font-mono">DXY</p><p className="font-mono font-bold">{fmt2(sig?.cross_asset_dxy as number | undefined)}</p></div>
              <div><p className="text-xs text-[#666] font-mono">VIX</p><p className="font-mono font-bold">{fmt2(sig?.cross_asset_vix as number | undefined)}</p></div>
              <div><p className="text-xs text-[#666] font-mono">WTI</p><p className="font-mono font-bold">{fmt2(sig?.cross_asset_oil as number | undefined)}</p></div>
              <div><p className="text-xs text-[#666] font-mono">US10Y (est)</p><p className="font-mono font-bold">4.45%</p></div>
            </div>
          </div>
        </div>
      </div>
      <div
        className="fixed inset-0 pointer-events-none z-[100] opacity-[0.02]"
        style={{
          backgroundImage: 'linear-gradient(to bottom, transparent 50%, rgba(0, 0, 0, 0.5) 50%)',
          backgroundSize: '100% 4px',
        }}
      />
      <div className="fixed inset-0 pointer-events-none z-[100] overflow-hidden opacity-[0.04]">
        <div
          className="w-full h-full animate-scanline"
          style={{
            background: 'linear-gradient(to bottom, transparent 0%, rgba(255,255,255,1) 10%, rgba(0,0,0,1) 50%, transparent 100%)',
          }}
        />
      </div>
      <div className={`${focusMode ? 'hidden' : ''} print:hidden`}><TerminalNav /></div>
      <div className="flex flex-1 overflow-hidden">
        <div className="hidden xl:flex flex-col w-12 border-r border-[#141414] bg-[#080808] items-center py-6 shrink-0 z-50 gap-8">
          {PAIRS.map((p) => {
            const isActive = p.urlSlug === pairSlug;
            return (
              <a
                key={p.label}
                href={`/terminal/fx-regime/${p.urlSlug}`}
                className="font-mono text-[10px] tracking-widest cursor-pointer transition-colors hover:text-[#fff]"
                style={{
                  writingMode: 'vertical-rl',
                  transform: 'rotate(180deg)',
                  color: isActive ? p.pairColor : '#444',
                  fontWeight: isActive ? 700 : 400,
                }}
              >
                {p.display}
              </a>
            );
          })}
        </div>

        <motion.div variants={container} initial="hidden" animate="show" className="flex-1 overflow-y-auto hide-scrollbar">
          <motion.div
            variants={item}
            className="sticky top-0 z-40 bg-[#080808] border-b border-[#141414] px-6 py-4 flex justify-between items-end"
          >
            <div className="flex items-end gap-6">
              <ClickToCopy value={sig?.spot != null ? Number(sig.spot).toFixed(pair.label === 'USDJPY' ? 2 : 4) : ''}>
                <div className="flex flex-col items-start cursor-pointer hover:opacity-80 transition-opacity">
                  <p className="font-mono text-[10px] tracking-[0.15em] mb-1.5" style={{ color: pair.pairColor }}>
                    {pair.label}
                  </p>
                  <div className="flex items-baseline gap-3">
                    <h1 className="font-mono text-4xl font-bold tracking-tight text-white m-0 tabular-nums">
                      {signalsQ.isPending ? '…' : sig?.spot != null ? Number(sig.spot).toFixed(pair.label === 'USDJPY' ? 2 : 4) : '—'}
                    </h1>
                    <span className="font-mono text-[13px] font-bold tabular-nums" style={{ color: chgObj.color }}>
                      {chgObj.str}
                    </span>
                  </div>
                  <p className="font-mono text-[9px] text-[#666] tracking-widest mt-1.5 uppercase">
                    SYNCED: {TODAY} {lastRunQ.data ? `${new Date(lastRunQ.data).toISOString().slice(11, 16)} UTC` : ''}
                  </p>
                </div>
              </ClickToCopy>
              <div className="pb-1.5 flex items-center gap-2">
                <span className="font-mono text-[10px] text-[#444] px-1.5 py-0.5 border border-[#1a1a1a] bg-[#0a0a0a]">
                  {mainErr ? 'ERROR' : 'SYNCED DATA'}
                </span>
              </div>
            </div>
            {/* Header action buttons */}
            <div className="flex items-center gap-2 print:hidden">
              <button
                type="button"
                onClick={() => setFocusMode((v) => !v)}
                className={`font-mono text-[9px] px-2.5 py-1.5 border tracking-widest transition-colors ${
                  focusMode
                    ? 'border-[#737373] text-[#e8e8e8] bg-[#1a1a1a]'
                    : 'border-[#1a1a1a] text-[#555] bg-[#0a0a0a] hover:text-[#aaa] hover:border-[#333]'
                }`}
                title="Press [F] to toggle"
              >
                {focusMode ? '[ EXIT FOCUS ]' : '[ FOCUS ]'}
              </button>
              <button
                type="button"
                onClick={handlePrint}
                className="font-mono text-[9px] px-2.5 py-1.5 border border-[#22c55e] text-[#22c55e] bg-[#0a0a0a] hover:bg-[#22c55e] hover:text-[#050505] tracking-widest transition-colors"
              >
                [ GENERATE RESEARCH BRIEF ]
              </button>
            </div>

            <div className="flex gap-10 text-right">
              <div className="flex items-center gap-4">
                <Sparkline values={rateSpark} width={40} height={16} color="#666" />
                <ClickToCopy value={fmt2((sig?.rate_diff_2y ?? sig?.rate_diff_10y) as number | undefined)}>
                  <p className="font-mono text-[9px] text-[#666] tracking-[0.1em] mb-1.5 uppercase flex items-center justify-end">Rate Diff <MethodologyPopover metricKey="rateDiff" /></p>
                  <p className="font-mono text-sm font-bold text-[#f2f2f2]">{fmt2((sig?.rate_diff_2y ?? sig?.rate_diff_10y) as number | undefined)}</p>
                </ClickToCopy>
              </div>
              <div className="flex items-center gap-4 border-l border-[#1a1a1a] pl-10">
                <div>
                  <p className="font-mono text-[9px] text-[#666] tracking-[0.1em] mb-1.5 uppercase flex items-center">Yield Curve (2Y | 10Y) <MethodologyPopover metricKey="rateDiff" /></p>
                  <div className="flex items-baseline gap-2">
                    <p className="font-mono text-sm font-bold text-[#f2f2f2] tabular-nums">
                      {fmt2(sig?.rate_diff_2y as number | undefined)} <span className="text-[#444] font-normal mx-1">|</span> {fmt2(sig?.rate_diff_10y as number | undefined)}
                    </p>
                    <span className={`font-mono text-[10px] ${curveTrendStr !== '—' ? (isSteepening ? 'text-[#22c55e]' : 'text-[#ef4444]') : 'text-[#737373]'}`}>
                      {curveTrendStr}
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4 border-l border-[#1a1a1a] pl-10">
                <Sparkline values={volSpark} width={40} height={16} color="#666" />
                <div>
                  <p className="font-mono text-[9px] text-[#666] tracking-[0.1em] mb-1.5 uppercase flex items-center justify-end">Realized Vol <MethodologyPopover metricKey="realizedVol" /></p>
                  <p className="font-mono text-sm font-bold text-[#f2f2f2]">{fmt2(sig?.realized_vol_20d as number | undefined)}%</p>
                </div>
              </div>
              <div className="flex items-center gap-4 border-l border-[#1a1a1a] pl-10">
                <Sparkline values={cotSpark} width={40} height={16} color="#666" />
                <div>
                  <p className="font-mono text-[9px] text-[#666] tracking-[0.1em] mb-1.5 uppercase flex items-center justify-end">COT Percentile <MethodologyPopover metricKey="cot" /></p>
                  <p className="font-mono text-sm font-bold text-[#f2f2f2]">{fmtInt(sig?.cot_percentile as number | undefined)}</p>
                </div>
              </div>
            </div>
          </motion.div>

          <div className="p-6 max-w-[1200px]">
            <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6 mb-6 items-start">
              <div className="flex flex-col gap-6">
                <motion.div variants={item} className="bg-[#050505] border border-[#1a1a1a] relative overflow-hidden group">
                  <div className="absolute top-0 left-0 w-1 h-full" style={{ background: pair.pairColor }} />
                <div className="px-5 py-4 border-b border-[#141414] flex justify-between items-center group/badge">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-[10px] text-[#888] tracking-widest">ACTIVE REGIME</span>
                    {!mainErr && !regimeQ.isPending && (
                      <div className="relative flex items-center">
                        <span className="font-mono text-[9px] text-[#050505] bg-[#22c55e] px-1.5 py-0.5 tracking-widest font-bold">
                          [ PIPELINE VERIFIED ]
                        </span>
                        <div className="absolute left-0 top-full mt-2 w-max bg-[#050505] border border-[#1a1a1a] px-2 py-1.5 opacity-0 group-hover/badge:opacity-100 transition-opacity pointer-events-none z-50">
                          <p className="font-mono text-[9px] text-[#aaa]">LAST SYNC: {TODAY} {lastRunQ.data ? `${new Date(lastRunQ.data).toISOString().slice(11, 19)} UTC` : ''}</p>
                        </div>
                      </div>
                    )}
                  </div>
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${mainErr ? 'bg-[#ef4444]' : regimeQ.isPending ? 'bg-[#737373]' : 'hidden'}`} />
                </div>
                <div className="px-5 py-5">
                  <p className="font-mono text-base font-bold text-white tracking-tight mb-4">
                    {regimeQ.isPending ? 'Loading…' : (call?.regime as string) ?? '—'}
                  </p>

                  <div className="mb-5">
                    <div className="flex justify-between items-baseline mb-1.5">
                      <span className="font-mono text-[9px] text-[#666] tracking-[0.1em]">CONFIDENCE</span>
                      <span className="font-mono text-lg font-bold" style={{ color: pair.pairColor }}>
                        {fmtPct(call?.confidence as number | undefined)}
                      </span>
                    </div>
                    <ConfidenceBar value={call?.confidence != null ? Number(call.confidence) : null} tone="dark" color={pair.pairColor} />
                  </div>

                  <div className="grid grid-cols-2 gap-px bg-[#1a1a1a] border border-[#1a1a1a] mb-5">
                    <div className="bg-[#0c0c0c] p-3">
                      <p className="font-mono text-[9px] text-[#666] mb-1 uppercase tracking-widest flex items-center">Composite <MethodologyPopover metricKey="composite" /></p>
                      <p className="font-mono text-xs text-white font-bold">{fmt2(call?.signal_composite as number | undefined)}</p>
                    </div>
                    <div className="bg-[#0c0c0c] p-3">
                      <p className="font-mono text-[9px] text-[#666] mb-1 uppercase tracking-widest">Rate Signal</p>
                      <p
                        className={`font-mono text-xs font-bold ${
                          call?.rate_signal === 'BULLISH'
                            ? 'text-[#22c55e]'
                            : call?.rate_signal === 'BEARISH'
                              ? 'text-[#ef4444]'
                              : 'text-[#737373]'
                        }`}
                      >
                        {(call?.rate_signal as string) ?? 'NEUTRAL'}
                      </p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-px bg-[#1a1a1a] border border-[#1a1a1a] mb-5">
                    <div className="bg-[#0c0c0c] p-3 col-span-2">
                      <p className="font-mono text-[9px] text-[#666] mb-1 uppercase tracking-widest">Yield Spread</p>
                      <p className="font-mono text-xs text-white font-bold tabular-nums">
                        {sig?.rate_diff_2y != null ? (
                          <>SPREAD [2Y] {fmt2(sig.rate_diff_2y as number)}</>
                        ) : sig?.rate_diff_10y != null ? (
                          <>SPREAD [10Y] {fmt2(sig.rate_diff_10y as number)}</>
                        ) : (
                          <>SPREAD [10Y] —</>
                        )}
                      </p>
                    </div>
                  </div>

                  <p className="font-sans text-[13px] text-[#aaa] leading-relaxed border-t border-[#141414] pt-4">
                    {(call?.primary_driver as string) ?? '—'}
                  </p>
                </div>
                </motion.div>

                <motion.div variants={item} className="bg-[#050505] border border-[#1a1a1a]">
                  <div className="px-5 py-3 border-b border-[#1a1a1a]">
                    <span className="font-mono text-[10px] text-[#737373] tracking-widest uppercase">Signal Anatomy</span>
                  </div>
                  <div className="grid grid-cols-4 divide-x divide-[#1a1a1a]">
                    {[
                      { label: 'RATES', sig: call?.rate_signal as string | null | undefined },
                      { label: 'COT', sig: call?.cot_signal as string | null | undefined },
                      { label: 'VOL', sig: call?.vol_signal as string | null | undefined },
                      { label: 'OI', sig: call?.oi_signal as string | null | undefined },
                    ].map(s => (
                      <div key={s.label} className="p-3 flex flex-col items-center justify-center gap-2">
                        <span className="font-mono text-[9px] text-[#555] tracking-widest">{s.label}</span>
                        <div className={`w-3 h-3 rounded-none ${s.sig === 'BULLISH' ? 'bg-[#22c55e]' : s.sig === 'BEARISH' ? 'bg-[#ef4444]' : 'bg-[#1a1a1a] border border-[#333]'}`} title={s.sig ?? 'NEUTRAL'} />
                      </div>
                    ))}
                  </div>
                </motion.div>
              </div>

              <motion.div
                variants={item}
                className="h-[360px] border border-[#1a1a1a] bg-[#0a0a0a] relative flex items-center justify-center overflow-hidden"
              >
                <div
                  className="absolute inset-0 opacity-10"
                  style={{
                    backgroundImage: 'radial-gradient(circle at 2px 2px, #333 1px, transparent 0)',
                    backgroundSize: '24px 24px',
                  }}
                />
                <div className="absolute inset-0 z-10">
                  <ClientChart
                    pairLabel={pair.label}
                    data={sigHistQ.data}
                    regimeData={regime30Q.data}
                    color={pair.pairColor}
                  />
                </div>
              </motion.div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <motion.div variants={item} className="border border-[#141414] bg-[#0c0c0c]">
                <div className="px-5 py-3 border-b border-[#141414]">
                  <span className="font-mono text-[10px] text-[#888] tracking-widest">REGIME HISTORY (7D)</span>
                </div>
                {historyQ.isPending ? (
                  <div className="p-6 font-mono text-[11px] text-[#666] animate-pulse">Loading history…</div>
                ) : (
                  <table className="w-full font-mono text-left">
                    <thead>
                      <tr className="border-b border-[#1a1a1a]">
                        <th className="px-5 py-2.5 text-[9px] text-[#555] font-normal tracking-widest">DATE</th>
                        <th className="px-5 py-2.5 text-[9px] text-[#555] font-normal tracking-widest">REGIME</th>
                        <th className="px-5 py-2.5 text-[9px] text-[#555] font-normal tracking-widest text-right">CONF</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.slice(0, 7).map((h, i) => (
                        <tr
                          key={`${h.date}-${i}`}
                          className={`border-b border-[#111] hover:bg-[#111] transition-colors ${i === 0 ? 'bg-[#0f0f0f]' : ''}`}
                        >
                          <td className="px-5 py-2.5 text-[11px] text-[#888]">{h.date.slice(5)}</td>
                          <td className="px-5 py-2.5 text-[10px] text-[#ccc] font-bold tracking-wide">{h.regime}</td>
                          <td className="px-5 py-2.5 text-[11px] text-[#aaa] text-right tabular-nums">{fmtPct(h.confidence)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </motion.div>

              <div className="flex flex-col gap-6">
                <motion.div variants={item} className="border border-[#141414] bg-[#0c0c0c] flex flex-col min-h-[280px]">
                  <div className="px-5 py-3 border-b border-[#141414] flex justify-between items-center bg-[#0d0d0d]">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] text-[#888] tracking-widest">[ PROPRIETARY SYSTEM ANALYSIS ]</span>
                    </div>
                  </div>
                  <div className="p-5 flex-1 text-[#888] font-mono text-[11px] leading-relaxed relative">
                    <div className="absolute inset-x-5 top-5 bottom-5 overflow-y-auto pr-2 hide-scrollbar">
                      {briefQ.isPending ? (
                        <p className="text-[#666] animate-pulse">Loading brief…</p>
                      ) : briefQ.isError ? (
                        <p className="text-[#ef4444]">Brief unavailable.</p>
                      ) : paragraphs.length ? (
                        paragraphs.map((para, i) => (
                          <motion.p
                            key={`${analysisText.slice(0, 20)}-${i}`}
                            initial={{ opacity: 0, y: 6 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.08 * i, duration: 0.25 }}
                            className={`mb-3 ${i === 0 ? 'text-[#ddd]' : 'text-[#b0b0b0]'}`}
                          >
                            {para}
                          </motion.p>
                        ))
                      ) : (
                        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-[#666]">
                          System analysis pending for this cycle.
                        </motion.p>
                      )}
                    </div>
                  </div>
                </motion.div>

                <motion.div variants={item} className="border border-[#141414] bg-[#0c0c0c] flex flex-col">
                  <div className="px-5 py-3 border-b border-[#141414] bg-[#0d0d0d]">
                    <span className="font-mono text-[10px] text-[#888] tracking-widest">RAW TELEMETRY</span>
                  </div>
                  <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div>
                      <p className="font-mono text-[9px] text-[#666] tracking-[0.1em] mb-3 uppercase">Yield Curve</p>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="font-mono text-[10px] text-[#888]">2Y Spread</span>
                          <span className="font-mono text-[11px] text-white font-bold tabular-nums">{fmt2(sig?.rate_diff_2y as number | undefined)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="font-mono text-[10px] text-[#888]">10Y Spread</span>
                          <span className="font-mono text-[11px] text-white font-bold tabular-nums">{fmt2(sig?.rate_diff_10y as number | undefined)}</span>
                        </div>
                      </div>
                    </div>
                    <div className="md:border-l md:border-[#1a1a1a] md:pl-6">
                      <p className="font-mono text-[9px] text-[#666] tracking-[0.1em] mb-3 uppercase">Vol Surface</p>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="font-mono text-[10px] text-[#888]">5D Realized</span>
                          <span className="font-mono text-[11px] text-white font-bold tabular-nums">{fmt2(sig?.realized_vol_5d as number | undefined)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="font-mono text-[10px] text-[#888]">20D Realized</span>
                          <span className="font-mono text-[11px] text-white font-bold tabular-nums">{fmt2(sig?.realized_vol_20d as number | undefined)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="font-mono text-[10px] text-[#888]">30D Implied</span>
                          <span className="font-mono text-[11px] text-white font-bold tabular-nums">{fmt2(sig?.implied_vol_30d as number | undefined)}%</span>
                        </div>
                      </div>
                    </div>
                    <div className="md:border-l md:border-[#1a1a1a] md:pl-6">
                      <p className="font-mono text-[9px] text-[#666] tracking-[0.1em] mb-3 uppercase">Cross Asset</p>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="font-mono text-[10px] text-[#888]">DXY</span>
                          <span className="font-mono text-[11px] text-white font-bold tabular-nums">{fmt2(sig?.cross_asset_dxy as number | undefined)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="font-mono text-[10px] text-[#888]">Crude (CL=F)</span>
                          <span className="font-mono text-[11px] text-white font-bold tabular-nums">{fmt2(sig?.cross_asset_oil as number | undefined)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              </div>
            </div>
          </div>
        </motion.div>

        <div className={`hidden xl:flex w-[300px] border-l border-[#141414] bg-[#080808] flex-col overflow-y-auto hide-scrollbar shrink-0 print:hidden ${focusMode ? 'xl:hidden' : ''}`}>
          <div className="p-4 border-b border-[#141414]">
            <p className="font-mono text-[9px] text-[#666] tracking-widest mb-4">UPCOMING EVENTS</p>
            {eventsQ.isPending ? (
              <div className="text-[11px] text-[#555] animate-pulse">Loading…</div>
            ) : (
              <CalendarTab events={events} todayIso={TODAY} />
            )}
            <button
              type="button"
              onClick={() => {
                window.location.href = '/calendar';
              }}
              className="w-full mt-5 py-2 border border-[#1a1a1a] bg-[#0c0c0c] text-[#888] font-mono text-[9px] tracking-widest hover:bg-[#111] hover:text-[#aaa] transition-colors"
            >
              VIEW FULL CALENDAR
            </button>
          </div>
          
          <SidebarRawTelemetry 
            cotNet={sig?.cot_lev_money_net as number | undefined}
            vol5d={sig?.realized_vol_5d as number | undefined}
            vol20d={sig?.realized_vol_20d as number | undefined}
            oiDelta={sig?.oi_delta as number | undefined}
            pairChg={sig?.day_change_pct as number | undefined}
          />

          {/* Regime Shift Log */}
          <div className="p-4 border-b border-[#141414]">
            <p className="font-mono text-[9px] text-[#666] tracking-widest mb-4">[ REGIME SHIFT LOG ]</p>
            {historyQ.isPending ? (
              <p className="font-mono text-[9px] text-[#555] animate-pulse">Loading…</p>
            ) : regimeShiftLog.length === 0 ? (
              <p className="font-mono text-[9px] text-[#555]">No regime transitions found in history.</p>
            ) : (
              <div className="space-y-4">
                {regimeShiftLog.map((shift, i) => (
                  <div key={i} className="border-l-2 border-[#1a1a1a] pl-3">
                    <p className="font-mono text-[9px] text-[#555] tracking-widest tabular-nums mb-0.5">{shift.date}</p>
                    <p className="font-mono text-[10px] text-[#e8e8e8]">
                      <span className={`${
                        shift.fromRegime === 'BULLISH' ? 'text-[#22c55e]' :
                        shift.fromRegime === 'BEARISH' ? 'text-[#ef4444]' : 'text-[#737373]'
                      }`}>{shift.fromRegime}</span>
                      <span className="text-[#444] mx-1">→</span>
                      <span className={`${
                        shift.toRegime === 'BULLISH' ? 'text-[#22c55e]' :
                        shift.toRegime === 'BEARISH' ? 'text-[#ef4444]' : 'text-[#737373]'
                      }`}>{shift.toRegime}</span>
                    </p>
                    <p className="font-mono text-[9px] text-[#555] tabular-nums mt-0.5">{shift.durationDays}d prior regime duration</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <button
        type="button"
        onClick={() => setDrawerOpen(true)}
        className="xl:hidden fixed bottom-6 right-6 w-14 h-14 bg-[#111] border border-[#333] text-white rounded-full flex items-center justify-center z-[150]"
      >
        <Menu size={24} />
      </button>

      {drawerOpen && (
        <div className="xl:hidden fixed inset-0 z-[200] bg-black/80 backdrop-blur-sm flex justify-end">
          <div className="w-[85%] max-w-[320px] bg-[#080808] border-l border-[#1a1a1a] h-full flex flex-col relative animate-in slide-in-from-right duration-300">
            <button type="button" onClick={() => setDrawerOpen(false)} className="absolute top-4 right-4 text-[#888] hover:text-white">
              <X size={24} />
            </button>

            <div className="p-6 overflow-y-auto mt-10">
              <p className="font-mono text-[10px] text-[#666] tracking-widest mb-4">OTHER DESKS</p>
              <div className="flex flex-col gap-3 mb-10">
                <a href="/terminal" className="font-mono text-sm text-[#ddd] flex items-center gap-2 mb-2 pb-2 border-b border-[#1a1a1a]">
                  ← Terminal Index
                </a>
                {PAIRS.map((p) => (
                  <a
                    key={p.label}
                    href={`/terminal/fx-regime/${p.urlSlug}`}
                    className="font-mono text-sm"
                    style={{ color: p.urlSlug === pairSlug ? p.pairColor : '#888' }}
                  >
                    {p.display}
                  </a>
                ))}
              </div>

              <p className="font-mono text-[10px] text-[#666] tracking-widest mb-4">UPCOMING EVENTS</p>
              <CalendarTab events={events} todayIso={TODAY} compact />
            </div>
          </div>
        </div>
      )}

      <style
        dangerouslySetInnerHTML={{
          __html: `
        .hide-scrollbar::-webkit-scrollbar { display: none; }
        .hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
      `,
        }}
      />
    </div>
  );
}
