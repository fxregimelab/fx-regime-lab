'use client';

import Link from 'next/link';
import { Nav } from '@/components/layout/nav';
import { Footer } from '@/components/layout/footer';
import { HeroRegimeCard } from '@/components/ui/hero-regime-card';
import { PairCard } from '@/components/ui/pair-card';
import { RegimeHeatmap } from '@/components/ui/regime-heatmap';
import { ValidationTable } from '@/components/ui/validation-table';
import { fmt2 } from '@/components/ui/utils';
import { PAIRS, BRAND } from '@/lib/mockData';
import {
  useLatestRegimeCalls,
  useLatestSignals,
  useLatestBrief,
  useCrossAssetPulse,
  useValidationLog,
  useLastPipelineRun,
} from '@/lib/queries';
import {
  mapValidationLogToTableRows,
  rolling7dAccuracyPct,
  callsValidatedSince,
} from '@/lib/validation-format';

function SkeletonBar() {
  return <div className="h-10 bg-[#f0f0f0] rounded animate-pulse" />;
}

export default function Home() {
  const regimeQ = useLatestRegimeCalls();
  const signalsQ = useLatestSignals();
  const validationQ = useValidationLog(400);
  const lastRunQ = useLastPipelineRun();
  const latestBriefQ = useLatestBrief();
  const pulseQ = useCrossAssetPulse();

  const calls = regimeQ.data;
  const sigs = signalsQ.data;
  const valRows = validationQ.data;

  const regimeErr = regimeQ.isError;
  const sigErr = signalsQ.isError;
  const heroStatus = regimeErr || sigErr ? 'error' : regimeQ.isPending || signalsQ.isPending ? 'pending' : 'live';

  const eurCall = calls?.EURUSD;
  const eurSig = sigs?.EURUSD;
  const asOfDay =
    (lastRunQ.data as string | undefined)?.slice(0, 10) ??
    (eurCall as { date?: string } | undefined)?.date ??
    new Date().toISOString().slice(0, 10);
  const pipelineClock = lastRunQ.data
    ? `${new Date(lastRunQ.data).toISOString().slice(11, 16)} UTC`
    : '—';

  const tableRows = mapValidationLogToTableRows(valRows, 6);
  const acc7 = rolling7dAccuracyPct(valRows ?? []);
  const callsSinceApr = callsValidatedSince(valRows, '2026-04-01');
  const statsLoading = validationQ.isPending;

  const liveHeader = regimeErr || sigErr;

  return (
    <>
      <Nav />
      <main className="flex-1 bg-white">
        <section className="max-w-[1152px] mx-auto pt-[72px] px-6 pb-16 grid grid-cols-1 lg:grid-cols-2 gap-16 items-start">
          <div>
            <div className="flex items-center gap-2.5 mb-7">
              <span
                className={`w-1.5 h-1.5 rounded-full shrink-0 ${liveHeader ? 'bg-[#f87171]' : 'bg-[#22c55e] live-indicator animate-pulse'}`}
              />
              <span className="font-mono text-[11px] text-[#737373] tracking-widest">
                {liveHeader ? 'OFFLINE · G10 FX · DAILY CALLS' : 'LIVE · G10 FX · DAILY CALLS'}
              </span>
            </div>
            <h1 className="font-sans font-extrabold text-[52px] leading-[1.05] text-[#0a0a0a] tracking-tight mb-6">
              Daily regime
              <br />
              calls. On the
              <br />
              record.
            </h1>
            <p className="font-sans text-base text-[#525252] leading-relaxed max-w-[440px] mb-8">
              G10 FX regime classification across EUR/USD, USD/JPY, and USD/INR. Composite signal from rate differentials, COT positioning,
              realized volatility, and open interest. Every call public before market open. Every outcome validated.
            </p>
            <div className="flex gap-3 flex-wrap items-center">
              <Link
                href="/brief"
                className="bg-[#0a0a0a] text-white font-sans font-semibold text-[13px] px-5 py-2.5 transition-opacity hover:opacity-90"
              >
                Read today&apos;s brief
              </Link>
              <Link
                href="/performance"
                className="text-[#0a0a0a] font-sans font-medium text-[13px] py-2.5 underline decoration-[#d0d0d0] underline-offset-4 hover:decoration-[#0a0a0a] transition-colors"
              >
                Validation log →
              </Link>
            </div>
            <div className="mt-9 flex items-center gap-2 pt-6 border-t border-[#f0f0f0]">
              <span
                className={`w-1.25 h-1.25 rounded-full shrink-0 ${lastRunQ.isError ? 'bg-[#f87171]' : 'bg-[#22c55e] live-indicator animate-pulse'}`}
              />
              <span className="font-mono text-[10px] text-[#a0a0a0] tracking-widest">
                PIPELINE · {asOfDay} {pipelineClock} · 3 pairs tracked
              </span>
            </div>
          </div>
          <div>
            {regimeQ.isPending || signalsQ.isPending ? (
              <div className="bg-[#080808] border border-[#1e1e1e] h-[420px] animate-pulse" />
            ) : (
              <HeroRegimeCard call={eurCall} signals={eurSig} connectionStatus={heroStatus} />
            )}
          </div>
        </section>

        <div className="border-t border-[#e5e5e5]" />

        <section className="border-b border-[#e5e5e5]">
          <div className="max-w-[1152px] mx-auto px-6 grid grid-cols-2 lg:grid-cols-4">
            {[
              { label: 'Pairs tracked', value: '3' },
              {
                label: 'Calls since April 2026',
                value: statsLoading ? '—' : String(callsSinceApr),
              },
              {
                label: '7-day accuracy',
                value: statsLoading || acc7 == null ? '—' : `${acc7.toFixed(1)}%`,
              },
              { label: 'Signal families', value: '4' },
            ].map((s, i) => (
              <div
                key={s.label}
                className={`py-[22px] ${i % 2 === 0 ? 'pr-6 border-r border-[#e5e5e5]' : 'pl-6'} ${i < 2 ? 'border-b border-[#e5e5e5] lg:border-b-0' : ''} lg:border-r lg:pr-6 lg:pl-6 ${i === 0 ? 'lg:pl-0' : ''} ${i === 3 ? 'lg:border-r-0' : ''}`}
              >
                {statsLoading ? (
                  <SkeletonBar />
                ) : (
                  <>
                    <p className="font-mono text-[26px] font-bold text-[#0a0a0a] tracking-tight mb-1">{s.value}</p>
                    <p className="font-mono text-[10px] text-[#a0a0a0] tracking-widest uppercase">{s.label}</p>
                  </>
                )}
              </div>
            ))}
          </div>
        </section>

        <section className="max-w-[1152px] mx-auto py-16 px-6">
          <div className="flex items-baseline justify-between mb-6">
            <div>
              <h2 className="font-sans font-bold text-xl text-[#0a0a0a] tracking-tight m-0">Live Regime Snapshot</h2>
              <p className="font-mono text-[11px] text-[#a0a0a0] mt-1.5">
                {asOfDay} · {pipelineClock}
              </p>
            </div>
            <Link
              href="/terminal"
              className="font-mono text-[11px] text-[#737373] bg-transparent border border-[#e5e5e5] px-[14px] py-2 hover:bg-[#fafafa] transition-colors"
            >
              Open terminal →
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-[1px] bg-[#e5e5e5] shadow-[0_0_0_1px_#e5e5e5]">
            {PAIRS.map((p) => (
              <PairCard
                key={p.label}
                pair={p}
                call={calls?.[p.label]}
                signals={sigs?.[p.label]}
              />
            ))}
          </div>
        </section>

        <section className="max-w-[1152px] mx-auto px-6 pb-12">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="border border-[#e5e5e5] p-5">
              <p className="font-mono text-[10px] text-[#a0a0a0] tracking-widest mb-2">GLOBAL SENTIMENT</p>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: 'VIX', v: pulseQ.data?.vix.value, c: pulseQ.data?.vix.change },
                  { label: 'DXY', v: pulseQ.data?.dxy.value, c: pulseQ.data?.dxy.change },
                  { label: 'CRUDE OIL', v: pulseQ.data?.oil.value, c: pulseQ.data?.oil.change },
                ].map((r) => (
                  <div key={r.label} className="border border-[#f0f0f0] p-3">
                    <p className="font-mono text-[9px] text-[#888] tracking-widest mb-1">{r.label}</p>
                    <p className="font-mono text-sm font-bold text-[#0a0a0a]">{fmt2(r.v as number | undefined)}</p>
                    <p className={`font-mono text-[10px] ${r.c != null && r.c >= 0 ? 'text-[#16a34a]' : 'text-[#dc2626]'}`}>
                      {r.c == null ? '—' : `${r.c >= 0 ? '+' : ''}${r.c.toFixed(2)} d/d`}
                    </p>
                  </div>
                ))}
              </div>
            </div>
            <div className="border border-[#e5e5e5] p-5">
              <p className="font-mono text-[10px] text-[#a0a0a0] tracking-widest mb-2">LIVE AI SUMMARY</p>
              {latestBriefQ.isPending ? (
                <div className="h-20 bg-[#f7f7f7] animate-pulse" />
              ) : (
                <p className="font-sans text-[13px] text-[#525252] leading-relaxed">
                  {latestBriefQ.data?.brief_text ?? 'No live global brief has been generated yet.'}
                </p>
              )}
            </div>
          </div>
        </section>

        <section className="max-w-[1152px] mx-auto px-6 pb-12">
          <div className="flex items-baseline justify-between mb-5">
            <div>
              <h2 className="font-sans font-bold text-xl text-[#0a0a0a] tracking-tight m-0">30-Day Regime View</h2>
              <p className="font-mono text-[11px] text-[#a0a0a0] mt-1.5">Cross-pair regime at a glance. Click a pair for detail.</p>
            </div>
          </div>
          <RegimeHeatmap />
        </section>

        <section className="bg-[#0a0a0a] border-y border-[#111]">
          <div className="max-w-[1152px] mx-auto py-14 px-6">
            <div className="flex items-start justify-between mb-7 flex-wrap gap-5">
              <div>
                <p className="font-mono text-[10px] text-[#444] tracking-widest mb-2">VALIDATION LOG</p>
                <h2 className="font-sans font-bold text-xl text-[#f2f2f2] tracking-tight m-0">Next-day outcome, on the record.</h2>
                <p className="font-sans text-[13px] text-[#525252] mt-2">
                  Every call validated the following trading day. No revisions, no ex-post edits.
                </p>
              </div>
              <div className="text-right">
                <p className="font-mono text-3xl font-bold text-[#22c55e] tracking-tight leading-none">
                  {acc7 == null ? '—' : `${acc7.toFixed(1)}%`}
                </p>
                <p className="font-mono text-[10px] text-[#444] tracking-widest mt-1">7-DAY ACCURACY</p>
              </div>
            </div>
            {validationQ.isPending ? (
              <div className="h-40 bg-[#111] animate-pulse border border-[#1e1e1e]" />
            ) : validationQ.isError ? (
              <p className="font-mono text-xs text-[#f87171]">Validation data unavailable.</p>
            ) : (
              <ValidationTable rows={tableRows} tone="dark" />
            )}
            <Link
              href="/performance"
              className="inline-block font-mono text-[11px] text-[#555] bg-transparent border border-[#1f1f1f] px-4 py-2 mt-4 hover:bg-[#111] transition-colors"
            >
              Full validation log →
            </Link>
          </div>
        </section>

        <section className="max-w-[1152px] mx-auto py-16 px-6">
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-16 items-start">
            <div>
              <p className="font-mono text-[10px] text-[#a0a0a0] tracking-widest mb-3.5">SIGNAL ARCHITECTURE</p>
              <h2 className="font-sans font-bold text-[28px] text-[#0a0a0a] tracking-tight leading-snug mb-4">
                Four signal
                <br />
                families. One
                <br />
                composite.
              </h2>
              <p className="font-sans text-sm text-[#737373] leading-relaxed">
                Each family is normalized to a percentile rank before weighting. The composite drives the regime label.
              </p>
            </div>
            <div className="border border-[#e5e5e5]">
              {[
                {
                  n: '01',
                  label: 'Rate Differentials',
                  desc: '2Y sovereign yield spreads. Primary driver of medium-term FX regime direction.',
                  color: BRAND.eurusd,
                },
                {
                  n: '02',
                  label: 'COT Positioning',
                  desc: 'CFTC weekly non-commercial net positions as percentile ranks. Crowd and reversal signals.',
                  color: BRAND.usdjpy,
                },
                {
                  n: '03',
                  label: 'Realized Volatility',
                  desc: '5d and 20d realized vs 30d implied. Vol gate forces VOL_EXPANDING above 90th pctile.',
                  color: BRAND.usdinr,
                },
                {
                  n: '04',
                  label: 'OI and Risk Reversals',
                  desc: 'Open interest flows and 25-delta risk reversals. INR-specific series included.',
                  color: '#888',
                },
              ].map((s, i) => (
                <div key={s.n} className={`flex items-start gap-5 p-5 ${i < 3 ? 'border-b border-[#e5e5e5]' : ''}`}>
                  <span className="font-mono text-[11px] font-bold min-w-[24px] pt-0.5" style={{ color: s.color }}>
                    {s.n}
                  </span>
                  <div>
                    <p className="font-sans font-semibold text-sm text-[#0a0a0a] mb-1">{s.label}</p>
                    <p className="font-sans text-[13px] text-[#737373] leading-relaxed">{s.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="border-y border-[#e5e5e5]">
          <div className="max-w-[1152px] mx-auto py-12 px-6 grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-16 items-start">
            <div>
              <p className="font-mono text-[10px] text-[#a0a0a0] tracking-widest mb-3.5">ABOUT</p>
              <h2 className="font-sans font-bold text-[22px] text-[#0a0a0a] tracking-tight m-0">Shreyash Sakhare</h2>
              <p className="font-mono text-[11px] text-[#a0a0a0] mt-1.5">EE Undergrad · Discretionary Macro Research</p>
            </div>
            <div>
              <p className="font-sans text-[15px] text-[#525252] leading-relaxed max-w-[580px] mb-5">
                Studying how G10 FX regimes form and break using rate differentials, COT positioning, and volatility. This site is the public
                trace of that work — dated calls, validated outcomes, no narrative added after the fact.
              </p>
              <div className="flex gap-5">
                <Link
                  href="/about"
                  className="font-sans text-[13px] font-medium text-[#0a0a0a] bg-transparent border border-[#e5e5e5] px-4 py-2 hover:bg-[#fafafa] transition-colors"
                >
                  About this project
                </Link>
                <Link
                  href="/brief"
                  className="font-sans text-[13px] font-medium text-[#737373] bg-transparent border-none py-2 underline decoration-[#d0d0d0] underline-offset-4 hover:decoration-[#737373] transition-colors"
                >
                  Today&apos;s brief →
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
