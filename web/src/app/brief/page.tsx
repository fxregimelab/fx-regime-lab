'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { Nav } from '@/components/layout/nav';
import { Footer } from '@/components/layout/footer';
import { MacroPulseBar, PULSE_BAR_H } from '@/components/ui/macro-pulse-bar';
import { PAIRS } from '@/lib/mockData';
import { fmt2, fmtInt } from '@/components/ui/utils';
import { useLatestRegimeCalls, useLatestSignals, useLatestBrief, usePairBrief, useLastPipelineRun } from '@/lib/queries';

const SHELL_NAV_H = 54;
const SHELL_TOP_OFFSET = PULSE_BAR_H + SHELL_NAV_H;

export default function BriefPage() {
  const router = useRouter();
  const [activePair, setActivePair] = React.useState('ALL');
  const regimeQ = useLatestRegimeCalls();
  const signalsQ = useLatestSignals();
  const briefLogQ = useLatestBrief();
  const lastRunQ = useLastPipelineRun();
  const pairBriefEur = usePairBrief('EURUSD');
  const pairBriefJpy = usePairBrief('USDJPY');
  const pairBriefInr = usePairBrief('USDINR');

  const pairBriefMap: Record<string, ReturnType<typeof usePairBrief>> = {
    EURUSD: pairBriefEur,
    USDJPY: pairBriefJpy,
    USDINR: pairBriefInr,
  };

  const calls = regimeQ.data;
  const sigs = signalsQ.data;
  const macroContext =
    (briefLogQ.data?.macro_context as string | null) ??
    (briefLogQ.data?.brief_text as string | null) ??
    'Macro context loads from `brief_log` after the pipeline run.';
  const TODAY =
    lastRunQ.data?.slice(0, 10) ??
    (briefLogQ.data?.date as string | undefined) ??
    (calls?.EURUSD as { date?: string } | undefined)?.date ??
    new Date().toISOString().slice(0, 10);

  return (
    <>
      <MacroPulseBar />
      <Nav />
      <main className="flex-1 bg-white" style={{ marginTop: `${SHELL_TOP_OFFSET}px` }}>
        <div className="max-w-[1152px] mx-auto px-6 py-12">
          <div className="flex justify-between items-start mb-10 pb-6 border-b border-[#e5e5e5]">
            <div>
              <div className="flex items-center gap-2.5 mb-2.5">
                <span
                  className={`w-1.5 h-1.5 shrink-0 ${regimeQ.isError || signalsQ.isError ? 'bg-[#ef4444]' : 'hidden'}`}
                />
                <span className="font-mono text-[11px] text-[#888] tracking-widest">MORNING BRIEF</span>
                <span className="font-mono text-[11px] text-[#ccc]">{TODAY}</span>
              </div>
              <h1 className="font-sans font-extrabold text-[32px] text-[#0a0a0a] tracking-tight m-0">Daily Brief — {TODAY}</h1>
            </div>
            <button
              type="button"
              onClick={() => router.push('/terminal')}
              className="font-mono text-[11px] text-[#555] bg-transparent border border-[#e5e5e5] px-4 py-2 hover:bg-[#fafafa] transition-colors whitespace-nowrap"
            >
              Open terminal →
            </button>
          </div>

          <div className="bg-[#fafafa] border border-[#e5e5e5] border-l-[3px] border-l-[#0a0a0a] p-5 mb-10">
            <p className="font-mono text-[10px] text-[#888] tracking-widest mb-2">MACRO CONTEXT</p>
            <p className="font-sans text-sm text-[#333] leading-relaxed">
              {briefLogQ.isPending ? 'Loading…' : macroContext}
            </p>
          </div>

          <div className="flex gap-[1px] mb-8 border-b border-[#e5e5e5]">
            {['ALL', ...PAIRS.map((p) => p.display)].map((label) => {
              const active = activePair === label;
              const pairMeta = PAIRS.find((p) => p.display === label);
              return (
                <button
                  key={label}
                  type="button"
                  onClick={() => setActivePair(label)}
                  className={`font-mono text-[11px] px-4 py-2.5 transition-colors -mb-[1px] tracking-wide ${active ? 'text-[#0a0a0a] font-bold border-b-2' : 'text-[#999] font-normal border-b-2 border-transparent'}`}
                  style={{ borderBottomColor: active ? pairMeta?.pairColor ?? '#0a0a0a' : 'transparent' }}
                >
                  {label}
                </button>
              );
            })}
          </div>

          <div className="flex flex-col gap-4">
            {PAIRS.filter((p) => activePair === 'ALL' || activePair === p.display).map((p) => {
              const call = calls?.[p.label];
              const sig = sigs?.[p.label];
              const pb = pairBriefMap[p.label];
              const analysis = (pb.data?.analysis as string | null) ?? '';
              const paras = analysis ? analysis.split(/\n\n+/).filter(Boolean) : [];
              const pct = call ? Math.round(Number(call.confidence) * 100) : null;
              const regimeLabel = (call?.regime as string) ?? (pb.data?.regime as string) ?? '—';
              const driver = (call?.primary_driver as string) ?? (pb.data?.primary_driver as string) ?? '';

              return (
                <div key={p.label} className="border border-[#e5e5e5] mb-4" style={{ borderTop: `3px solid ${p.pairColor}` }}>
                  <div className="grid grid-cols-[1fr_auto] items-start gap-6 p-6 border-b border-[#f0f0f0] bg-[#fafafa]">
                    <div>
                      <div className="flex items-center gap-3 mb-2">
                        <span className="font-mono text-sm font-bold" style={{ color: p.pairColor }}>
                          {p.display}
                        </span>
                        <span className="font-mono text-[11px] font-bold text-[#0a0a0a] bg-[#f0f0f0] px-2 py-0.5 tracking-wide">
                          {regimeLabel}
                        </span>
                      </div>
                      <p className="font-sans text-[13px] text-[#737373] leading-relaxed">{driver || '—'}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-2xl font-bold tracking-tight leading-none" style={{ color: p.pairColor }}>
                        {pct ?? '—'}
                        <span className="text-xs text-[#aaa] font-normal">{pct != null ? '%' : ''}</span>
                      </p>
                      <p className="font-mono text-[9px] text-[#aaa] tracking-widest mt-1.5">CONFIDENCE</p>
                      <div className="mt-1.5 w-20 ml-auto h-[2px] bg-[#ebebeb]">
                        <div className="h-full transition-all" style={{ width: `${pct ?? 0}%`, background: p.pairColor }} />
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-5 border-b border-[#f0f0f0]">
                    {[
                      ['SPOT', sig?.spot != null ? Number(sig.spot).toFixed(p.label === 'USDJPY' ? 2 : 4) : '—'],
                      ['RATE DIFF 2Y', fmt2(sig?.rate_diff_2y as number | undefined)],
                      ['COT PCTILE', fmtInt(sig?.cot_percentile as number | undefined)],
                      ['RVOL 20D', fmt2(sig?.realized_vol_20d as number | undefined)],
                      ['COMPOSITE', fmt2(call?.signal_composite as number | undefined)],
                    ].map(([label, value], i) => (
                      <div key={label} className={`px-4 py-3.5 ${i < 4 ? 'border-r border-[#f0f0f0]' : ''}`}>
                        <p className="font-mono text-[9px] text-[#aaa] tracking-widest mb-1.5">{label}</p>
                        <p className="font-mono text-sm font-bold text-[#0a0a0a]">{value as string}</p>
                      </div>
                    ))}
                  </div>

                  <div className="px-6 py-5">
                    {pb.isPending ? (
                      <p className="font-mono text-[13px] text-[#999] animate-pulse">Loading AI brief…</p>
                    ) : paras.length ? (
                      paras.map((para, i) => (
                        <p
                          key={i}
                          className={`font-sans text-[15px] leading-[1.75] mb-3 ${i === 1 ? 'text-[#111] font-medium' : 'text-[#444] font-normal'}`}
                        >
                          {para}
                        </p>
                      ))
                    ) : (
                      <p className="font-sans text-[15px] text-[#888]">No stored brief for this pair yet.</p>
                    )}
                    <button
                      type="button"
                      onClick={() => router.push(`/terminal/fx-regime/${p.urlSlug}`)}
                      className="font-mono text-[11px] bg-transparent px-3.5 py-1.5 cursor-pointer mt-2 hover:opacity-80 transition-opacity"
                      style={{ color: p.pairColor, border: `1px solid ${p.pairColor}40` }}
                    >
                      Open {p.display} desk →
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-10 pt-6 border-t border-[#e5e5e5]">
            <p className="font-mono text-[10px] text-[#c0c0c0] tracking-widest leading-[1.8]">
              RESEARCH AND LEARNING ONLY. NOT INVESTMENT ADVICE. ALL CALLS LOGGED PRIOR TO MARKET OPEN. OUTCOMES VALIDATED NEXT TRADING DAY.
            </p>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
