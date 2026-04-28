'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';
import { useParams } from 'next/navigation';
import { TerminalNav, TERMINAL_NAV_H } from '@/components/layout/terminal-nav';
import { MethodologyPopover } from '@/components/ui/methodology-popover';
import { ResearchReport } from '@/components/ui/research-report';
import { PAIRS } from '@/lib/mockData';
import { fmt2, fmtInt, fmtKM, fmtPct, fmtChg } from '@/components/ui/utils';
import {
  useLatestRegimeCalls,
  useLatestSignals,
  useUpcomingMacroEvents,
  usePairBrief,
  useSignalHistory,
  useLastPipelineRun,
  useRegimeHistory30D,
  useLatestResearchAnalogs,
} from '@/lib/queries';
import type { Database } from '@/lib/supabase/database.types';

const TradingViewChart = dynamic(() => import('@/components/ui/trading-view-chart'), {
  ssr: false,
  loading: () => <p className="font-mono text-[11px] text-[#444]">[ Loading TradingView Container... ]</p>,
});

type MacroEventRow = Database['public']['Tables']['macro_events']['Row'];

function naCell() {
  return <span className="font-mono text-[11px] text-[#444] tabular-nums">[ N/A ]</span>;
}

function signalTone(signal?: string | null) {
  if (signal === 'BULLISH') return { dot: 'bg-[#22c55e]', text: 'text-[#22c55e]', icon: '▲' };
  if (signal === 'BEARISH') return { dot: 'bg-[#ef4444]', text: 'text-[#ef4444]', icon: '▼' };
  return { dot: 'bg-[#444]', text: 'text-[#777]', icon: '■' };
}

export default function PairDeskPage() {
  const params = useParams();
  const pairSlug = params.pair as string;
  const pair = PAIRS.find((p) => p.urlSlug === pairSlug) ?? PAIRS[0];

  const regimeQ = useLatestRegimeCalls();
  const signalsQ = useLatestSignals();
  const eventsQ = useUpcomingMacroEvents();
  const briefQ = usePairBrief(pair.label);
  const sigHistQ = useSignalHistory(pair.label, 365);
  const regime30Q = useRegimeHistory30D(pair.label);
  const lastRunQ = useLastPipelineRun();
  const analogQ = useLatestResearchAnalogs(pair.label);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);

  const call = regimeQ.data?.[pair.label];
  const sig = signalsQ.data?.[pair.label];
  const chgObj = fmtChg(sig?.day_change_pct as number | undefined);
  const analysisText = (briefQ.data?.analysis as string | null) ?? '';
  const paragraphs = analysisText ? analysisText.split(/\n\n+/).filter(Boolean) : [];
  const today =
    lastRunQ.data?.slice(0, 10) ??
    (call as { date?: string } | undefined)?.date ??
    new Date().toISOString().slice(0, 10);

  const events: MacroEventRow[] = useMemo(
    () =>
      ((eventsQ.data ?? []) as MacroEventRow[])
        .filter((e) => !e.pairs?.length || e.pairs.includes(pair.label))
        .slice(0, 6),
    [eventsQ.data, pair.label],
  );

  const rateDisplay =
    sig?.rate_diff_2y == null ? naCell() : <span className="font-mono text-[12px] font-extrabold text-[#ffffff] tabular-nums">{fmt2(sig.rate_diff_2y as number)}</span>;
  const cotDisplay =
    sig?.cot_lev_money_net == null ? naCell() : <span className="font-mono text-[12px] font-extrabold text-[#ffffff] tabular-nums">{fmtKM(sig.cot_lev_money_net as number)}</span>;

  const handleGenerateReport = async () => {
    setIsGeneratingReport(true);
    try {
      await Promise.all([
        regimeQ.refetch(),
        signalsQ.refetch(),
        briefQ.refetch(),
        analogQ.refetch(),
        sigHistQ.refetch(),
      ]);
      await new Promise((resolve) => setTimeout(resolve, 400));
      window.print();
    } finally {
      setIsGeneratingReport(false);
    }
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.35 }} className="min-h-screen bg-[#000000] text-[#e8e8e8]">
      <ResearchReport
        pair={pair}
        today={today}
        call={call}
        sig={sig}
        analysisText={analysisText}
        analogs={analogQ.data ?? []}
        history={(sigHistQ.data ?? []).map((r) => ({
          date: String(r.date),
          spot: r.spot,
          rate_diff_2y: r.rate_diff_2y,
          rate_diff_10y: r.rate_diff_10y,
          cot_lev_money_net: r.cot_lev_money_net,
        }))}
      />
      <TerminalNav />

      <div
        className="grid grid-cols-1 xl:grid-cols-[72px_minmax(0,1fr)_340px] min-h-[calc(100vh-104px)]"
        style={{ marginTop: `${TERMINAL_NAV_H}px` }}
      >
        <aside className="hidden xl:flex flex-col border-r border-[#111] bg-[#000000]">
          <div className="flex-1 py-4">
            {PAIRS.map((p) => {
              const active = p.urlSlug === pairSlug;
              const pairSig = signalsQ.data?.[p.label];
              return (
                <Link
                  key={p.label}
                  href={`/terminal/fx-regime/${p.urlSlug}`}
                  className={`h-[96px] border-b border-[#111] px-2 flex flex-col justify-center items-center ${active ? 'bg-[#060606]' : 'hover:bg-[#040404]'}`}
                >
                  <span className="font-mono text-[10px] tracking-widest" style={{ color: p.pairColor }}>
                    {p.label}
                  </span>
                  <span className="font-mono text-[11px] text-[#bdbdbd] tabular-nums mt-1">
                    {pairSig?.spot != null ? Number(pairSig.spot).toFixed(p.label === 'USDJPY' ? 2 : 4) : '--'}
                  </span>
                </Link>
              );
            })}
          </div>
        </aside>

        <main className="border-r border-[#111] bg-[#000000]">
          <section className="border-b border-[#111] px-6 py-5">
            <div className="flex items-center justify-between mb-2">
              <p className="font-mono text-[9px] text-[#666] tracking-widest">{pair.display}</p>
              <span className="font-mono text-[9px] font-bold text-[#d4d4d4] tracking-widest border border-[#111] bg-[#000000] px-2 py-1">
                [ PIPELINE VERIFIED ]
              </span>
            </div>
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <h1 className="font-mono text-6xl leading-none font-bold text-white tabular-nums">
                  {sig?.spot != null ? Number(sig.spot).toFixed(pair.label === 'USDJPY' ? 2 : 4) : '--'}
                </h1>
                <p className={`font-mono text-[12px] tabular-nums mt-2 ${chgObj.color}`}>{chgObj.str}</p>
              </div>
              <div className="text-right">
                <p className="font-mono text-[9px] text-[#666] tracking-widest">ACTIVE REGIME</p>
                <p className="font-mono text-[22px] font-extrabold text-[#ffffff] mt-1 tabular-nums">{(call?.regime as string) ?? '—'}</p>
                <p className="font-mono text-[9px] text-[#9b9b9b] mt-1 tracking-widest">CONFIDENCE</p>
                <p className="font-mono text-[14px] text-[#ffffff] font-extrabold mt-1 tabular-nums">{fmtPct(call?.confidence as number | undefined)}</p>
                <p className="font-mono text-[9px] text-[#555] mt-1 tracking-widest tabular-nums">{today}</p>
              </div>
            </div>
            <div className="mt-4 print:hidden">
              <button
                type="button"
                onClick={handleGenerateReport}
                disabled={isGeneratingReport}
                className="font-mono text-[10px] px-3 py-2 border border-[#111] bg-[#000] text-[#d4d4d4] tracking-widest hover:text-white disabled:opacity-60"
              >
                {isGeneratingReport ? 'Generating Report...' : '[ GENERATE RESEARCH BRIEF ]'}
              </button>
            </div>
          </section>

          <section className="grid grid-cols-1 md:grid-cols-4 gap-0 border-b border-[#111]">
            {[
              { key: 'RATES', signal: call?.rate_signal as string | null | undefined, value: rateDisplay, extra: <MethodologyPopover metricKey="rateDiff" /> },
              { key: 'COT', signal: call?.cot_signal as string | null | undefined, value: cotDisplay, extra: <MethodologyPopover metricKey="cot" /> },
              {
                key: 'VOL',
                signal: call?.vol_signal as string | null | undefined,
                value: <span className="font-mono text-[12px] font-extrabold text-[#ffffff] tabular-nums">{fmt2(sig?.realized_vol_20d as number | undefined)}%</span>,
                extra: <MethodologyPopover metricKey="realizedVol" />,
              },
              {
                key: 'OI',
                signal: call?.oi_signal as string | null | undefined,
                value:
                  sig?.oi_delta == null ? naCell() : <span className="font-mono text-[12px] font-extrabold text-[#ffffff] tabular-nums">{fmtKM(sig.oi_delta as number)}</span>,
                extra: null,
              },
            ].map((box) => {
              const tone = signalTone(box.signal);
              return (
                <div key={box.key} className="h-[110px] border-r border-b border-[#111] md:border-b-0 md:last:border-r-0 p-4 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[9px] text-[#777] tracking-widest">
                      {box.key} {box.extra}
                    </span>
                    <span className={`font-mono text-[11px] ${tone.text} tabular-nums`}>{tone.icon}</span>
                  </div>
                  <div className="h-[22px] flex items-center">{box.value}</div>
                  <span className={`font-mono text-[11px] font-extrabold ${tone.text} tabular-nums`}>{box.signal ?? 'NEUTRAL'}</span>
                </div>
              );
            })}
          </section>

          <section className="px-6 py-5">
            <div className="h-[560px] bg-[#000000] flex items-center justify-center relative rounded-none">
              <div className="absolute top-3 left-3 font-mono text-[10px] text-[#666] tracking-widest">CHART CONTAINER</div>
              <div className="absolute inset-0">
                <TradingViewChart pairLabel={pair.label} data={sigHistQ.data} regimeData={regime30Q.data} color={pair.pairColor} />
              </div>
            </div>
          </section>
        </main>

        <aside className="bg-[#000000] px-5 py-5">
          <section className="mb-8">
            <p className="font-mono text-[10px] text-[#666] tracking-widest mb-3">AI ANALYSIS</p>
            {briefQ.isPending ? (
              <p className="font-sans text-[13px] text-[#555]">Loading analysis...</p>
            ) : paragraphs.length ? (
              paragraphs.slice(0, 4).map((paragraph, idx) => (
                <p key={`${idx}-${paragraph.slice(0, 10)}`} className="font-sans text-[13px] text-[#bcbcbc] leading-relaxed mb-3">
                  {paragraph}
                </p>
              ))
            ) : (
              <p className="font-sans text-[13px] text-[#555]">No analysis available for this cycle.</p>
            )}
          </section>

          <section className="mb-8 border-t border-[#111] pt-5">
            <p className="font-mono text-[10px] text-[#666] tracking-widest mb-3">RAW TELEMETRY</p>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2">
              <span className="font-mono text-[10px] text-[#666]">2Y RATE</span>
              <span className="font-mono text-[10px] text-[#d4d4d4] text-right tabular-nums">{sig?.rate_diff_2y == null ? '[ N/A ]' : fmt2(sig.rate_diff_2y as number)}</span>
              <span className="font-mono text-[10px] text-[#666]">10Y RATE</span>
              <span className="font-mono text-[10px] text-[#d4d4d4] text-right tabular-nums">{sig?.rate_diff_10y == null ? '[ N/A ]' : fmt2(sig.rate_diff_10y as number)}</span>
              <span className="font-mono text-[10px] text-[#666]">COT NET</span>
              <span className="font-mono text-[10px] text-[#d4d4d4] text-right tabular-nums">{sig?.cot_lev_money_net == null ? '[ N/A ]' : fmtKM(sig.cot_lev_money_net as number)}</span>
              <span className="font-mono text-[10px] text-[#666]">VOL 20D</span>
              <span className="font-mono text-[10px] text-[#d4d4d4] text-right tabular-nums">{fmt2(sig?.realized_vol_20d as number | undefined)}%</span>
              <span className="font-mono text-[10px] text-[#666]">OI DELTA</span>
              <span className="font-mono text-[10px] text-[#d4d4d4] text-right tabular-nums">{sig?.oi_delta == null ? '[ N/A ]' : fmtKM(sig.oi_delta as number)}</span>
              <span className="font-mono text-[10px] text-[#666]">COT %ILE</span>
              <span className="font-mono text-[10px] text-[#d4d4d4] text-right tabular-nums">{fmtInt(sig?.cot_percentile as number | undefined)}</span>
            </div>
          </section>

          <section className="mb-8 border-t border-[#111] pt-5">
            <p className="font-mono text-[10px] text-[#666] tracking-widest mb-3">[ HISTORICAL CONTEXT ]</p>
            {analogQ.isPending ? (
              <p className="font-mono text-[10px] text-[#888]">Loading analog engine...</p>
            ) : analogQ.data?.length ? (
              <>
                <p className="font-mono text-[11px] text-[#e8e8e8] leading-relaxed">
                  ANALOG MATCH:{' '}
                  <span className="tabular-nums">
                    {`${Math.round(analogQ.data[0].match_score)}%`}
                  </span>{' '}
                  match with{' '}
                  <span className="tabular-nums">
                    {new Date(analogQ.data[0].match_date).toLocaleString('en-US', { month: 'short', year: 'numeric' })}
                  </span>{' '}
                  ({analogQ.data[0].context_label ?? 'Historical Regime'}).
                </p>
                <p className="font-mono text-[10px] text-[#888] mt-2">
                  FWD 30D RETURN (HISTORIC):{' '}
                  <span className="text-[#d4d4d4] tabular-nums">
                    {`${((analogQ.data.reduce((acc, r) => acc + (r.forward_30d_return ?? 0), 0) / analogQ.data.length) || 0).toFixed(2)}% (avg)`}
                  </span>
                </p>
                <p className="font-mono text-[10px] text-[#888] mt-1">
                  REGIME STABILITY:{' '}
                  <span className="text-[#d4d4d4] tabular-nums">
                    {`${((analogQ.data.reduce((acc, r) => acc + (r.regime_stability ?? 0), 0) / analogQ.data.length) || 0).toFixed(0)}% (High)`}
                  </span>
                </p>
              </>
            ) : (
              <p className="font-mono text-[10px] text-[#888]">No historical analogs available yet.</p>
            )}
          </section>

          <section className="border-t border-[#111] pt-5">
            <p className="font-mono text-[10px] text-[#666] tracking-widest mb-3">CALENDAR IMPACT</p>
            {eventsQ.isPending ? (
              <p className="font-mono text-[10px] text-[#555]">Loading events...</p>
            ) : events.length ? (
              <div className="space-y-2">
                {events.map((event) => (
                  <div key={event.id} className="border-b border-[#111] pb-2">
                    <p className="font-mono text-[10px] text-[#d0d0d0]">{event.event_name ?? 'Macro Event'}</p>
                    <p className="font-mono text-[9px] text-[#666] tabular-nums">{event.date} · {event.currency ?? 'FX'}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="font-mono text-[10px] text-[#555]">No upcoming events for this pair.</p>
            )}
          </section>
        </aside>
      </div>
    </motion.div>
  );
}
