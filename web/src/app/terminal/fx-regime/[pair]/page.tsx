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
  useUpcomingMacroEvents,
  usePairBrief,
  useSignalHistory,
  useLastPipelineRun,
  sparkNumericSeries,
} from '@/lib/queries';
import { CalendarTab } from '@/app/terminal/calendar-tab';
import type { Database } from '@/lib/supabase/database.types';

const ClientChart = dynamic(() => import('@/components/ui/client-chart'), {
  ssr: false,
  loading: () => <p className="font-mono text-[11px] text-[#444] z-10">[ Loading Chart... ]</p>,
});

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } };
const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.2, ease: 'easeOut' as const } },
};
type MacroEventRow = Database['public']['Tables']['macro_events']['Row'];

export default function PairDeskPage() {
  const params = useParams();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const pairSlug = params.pair as string;
  const pair = PAIRS.find((p) => p.urlSlug === pairSlug) ?? PAIRS[0];

  const regimeQ = useLatestRegimeCalls();
  const signalsQ = useLatestSignals();
  const historyQ = useRegimeHistory(pair.label);
  const eventsQ = useUpcomingMacroEvents();
  const briefQ = usePairBrief(pair.label);
  const sigHistQ = useSignalHistory(pair.label, 14);
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

  const chgObj = fmtChg(sig?.day_change_pct as number | undefined);

  const TODAY =
    lastRunQ.data?.slice(0, 10) ??
    (call as { date?: string } | undefined)?.date ??
    new Date().toISOString().slice(0, 10);

  const analysisText = (briefQ.data?.analysis as string | null) ?? '';
  const paragraphs = analysisText ? analysisText.split(/\n\n+/).filter(Boolean) : [];

  return (
    <div className="min-h-screen flex flex-col bg-[#050505] text-[#e8e8e8] relative">
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
      <TerminalNav />
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
            className="sticky top-0 z-40 bg-[#080808] border-b border-[#141414] px-6 py-4 flex justify-between items-end shadow-[0_10px_30px_rgba(0,0,0,0.4)]"
          >
            <div className="flex items-end gap-6">
              <ClickToCopy value={sig?.spot != null ? Number(sig.spot).toFixed(pair.label === 'USDJPY' ? 2 : 4) : ''}>
                <div className="flex flex-col items-start cursor-pointer hover:opacity-80 transition-opacity">
                  <p className="font-mono text-[10px] tracking-[0.15em] mb-1.5" style={{ color: pair.pairColor }}>
                    {pair.label}
                  </p>
                  <div className="flex items-baseline gap-3">
                    <h1 className="font-mono text-4xl font-bold tracking-tight text-white m-0">
                      {signalsQ.isPending ? '…' : sig?.spot != null ? Number(sig.spot).toFixed(pair.label === 'USDJPY' ? 2 : 4) : '—'}
                    </h1>
                    <span className="font-mono text-[13px] font-bold" style={{ color: chgObj.color }}>
                      {chgObj.str}
                    </span>
                  </div>
                </div>
              </ClickToCopy>
              <div className="pb-1.5 flex items-center gap-2">
                <span
                  className={`w-1.5 h-1.5 rounded-full shrink-0 ${mainErr ? 'bg-[#f87171]' : signalsQ.isPending ? 'bg-[#737373]' : 'live-indicator animate-pulse'}`}
                />
                <span className="font-mono text-[10px] text-[#444] px-1.5 py-0.5 border border-[#1a1a1a] bg-[#0a0a0a]">
                  {mainErr ? 'ERROR' : 'LIVE SPOT'}
                </span>
              </div>
            </div>

            <div className="flex gap-10 text-right">
              <div className="flex items-center gap-4">
                <Sparkline values={rateSpark} width={40} height={16} color="#666" />
                <ClickToCopy value={fmt2(sig?.rate_diff_2y as number | undefined)}>
                  <p className="font-mono text-[9px] text-[#666] tracking-[0.1em] mb-1.5 uppercase">Rate Diff 2Y</p>
                  <p className="font-mono text-sm font-bold text-[#f2f2f2]">{fmt2(sig?.rate_diff_2y as number | undefined)}</p>
                </ClickToCopy>
              </div>
              <div className="flex items-center gap-4 border-l border-[#1a1a1a] pl-10">
                <div>
                  <p className="font-mono text-[9px] text-[#666] tracking-[0.1em] mb-1.5 uppercase">Rate Regime</p>
                  <p className="font-mono text-sm font-bold text-[#f2f2f2]">
                    {fmt2(sig?.rate_diff_2y as number | undefined)} / {fmt2(sig?.rate_diff_10y as number | undefined)}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4 border-l border-[#1a1a1a] pl-10">
                <Sparkline values={volSpark} width={40} height={16} color="#666" />
                <div>
                  <p className="font-mono text-[9px] text-[#666] tracking-[0.1em] mb-1.5 uppercase">Realized Vol</p>
                  <p className="font-mono text-sm font-bold text-[#f2f2f2]">{fmt2(sig?.realized_vol_20d as number | undefined)}%</p>
                </div>
              </div>
              <div className="flex items-center gap-4 border-l border-[#1a1a1a] pl-10">
                <Sparkline values={cotSpark} width={40} height={16} color="#666" />
                <div>
                  <p className="font-mono text-[9px] text-[#666] tracking-[0.1em] mb-1.5 uppercase">COT Percentile</p>
                  <p className="font-mono text-sm font-bold text-[#f2f2f2]">{fmtInt(sig?.cot_percentile as number | undefined)}</p>
                </div>
              </div>
            </div>
          </motion.div>

          <div className="p-6 max-w-[1200px]">
            <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6 mb-6 items-start">
              <motion.div variants={item} className="bg-[#0c0c0c] border border-[#1e1e1e] relative overflow-hidden group">
                <div className="absolute top-0 left-0 w-1 h-full" style={{ background: pair.pairColor }} />
                <div className="px-5 py-4 border-b border-[#141414] flex justify-between items-center">
                  <span className="font-mono text-[10px] text-[#888] tracking-widest">ACTIVE REGIME</span>
                  <span
                    className={`w-1.5 h-1.5 rounded-full shrink-0 ${mainErr ? 'bg-[#f87171]' : regimeQ.isPending ? 'bg-[#737373]' : 'live-indicator animate-pulse'}`}
                  />
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
                      <p className="font-mono text-[9px] text-[#666] mb-1 uppercase tracking-widest">Composite</p>
                      <p className="font-mono text-xs text-white font-bold">{fmt2(call?.signal_composite as number | undefined)}</p>
                    </div>
                    <div className="bg-[#0c0c0c] p-3">
                      <p className="font-mono text-[9px] text-[#666] mb-1 uppercase tracking-widest">Rate Signal</p>
                      <p
                        className={`font-mono text-xs font-bold ${
                          call?.rate_signal === 'BULLISH'
                            ? 'text-[#4ade80]'
                            : call?.rate_signal === 'BEARISH'
                              ? 'text-[#f87171]'
                              : 'text-[#888]'
                        }`}
                      >
                        {(call?.rate_signal as string) ?? 'NEUTRAL'}
                      </p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-px bg-[#1a1a1a] border border-[#1a1a1a] mb-5">
                    <div className="bg-[#0c0c0c] p-3">
                      <p className="font-mono text-[9px] text-[#666] mb-1 uppercase tracking-widest">Yield Curve Spread</p>
                      <p className="font-mono text-xs text-white font-bold">
                        2Y {fmt2(sig?.rate_diff_2y as number | undefined)}
                      </p>
                    </div>
                    <div className="bg-[#0c0c0c] p-3">
                      <p className="font-mono text-[9px] text-[#666] mb-1 uppercase tracking-widest">Rate Regime</p>
                      <p className="font-mono text-xs text-white font-bold">
                        10Y {fmt2(sig?.rate_diff_10y as number | undefined)}
                      </p>
                    </div>
                  </div>

                  <p className="font-sans text-[13px] text-[#aaa] leading-relaxed border-t border-[#141414] pt-4">
                    {(call?.primary_driver as string) ?? '—'}
                  </p>
                </div>
              </motion.div>

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
                  <ClientChart pairLabel={pair.label} data={sigHistQ.data as any} color={pair.pairColor} />
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

              <motion.div variants={item} className="border border-[#141414] bg-[#0c0c0c] flex flex-col min-h-[280px]">
                <div className="px-5 py-3 border-b border-[#141414] flex justify-between items-center bg-[#0d0d0d]">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] text-[#888] tracking-widest">AI ANALYSIS</span>
                    <span className="font-mono text-[9px] px-1 bg-[#1a1a1a] text-[#aaa] border border-[#222]">OPENROUTER M1</span>
                  </div>
                </div>
                <div className="p-5 flex-1 text-[#888] font-mono text-[11px] leading-relaxed relative">
                  <div className="absolute inset-x-5 top-5 bottom-5 overflow-y-auto pr-2 hide-scrollbar">
                    {briefQ.isPending ? (
                      <p className="text-[#666] animate-pulse">Loading brief…</p>
                    ) : briefQ.isError ? (
                      <p className="text-[#f87171]">Brief unavailable.</p>
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
                        No AI brief stored for {pair.display} yet. Pipeline writes the `brief` table after the weekly OpenRouter pass.
                      </motion.p>
                    )}
                  </div>
                </div>
              </motion.div>
            </div>
          </div>
        </motion.div>

        <div className="hidden xl:flex w-[300px] border-l border-[#141414] bg-[#080808] flex-col hide-scrollbar shrink-0">
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
        </div>
      </div>

      <button
        type="button"
        onClick={() => setDrawerOpen(true)}
        className="xl:hidden fixed bottom-6 right-6 w-14 h-14 bg-[#111] border border-[#333] text-white rounded-full flex items-center justify-center shadow-2xl z-[150]"
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
