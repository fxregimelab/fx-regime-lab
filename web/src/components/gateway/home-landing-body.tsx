'use client';

import React from 'react';
import Link from 'next/link';
import { DeskCard, DeskCardTelemetryRow } from '@/components/ui/desk-card';
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
  useLatestDeskOpenCardsSnapshot,
} from '@/lib/queries';
import type { GatewayLandingPayload } from '@/lib/queries';
import {
  mapValidationLogToTableRows,
  rolling7dAccuracyPct,
  callsValidatedSince,
} from '@/lib/validation-format';

function pairDisplay(label: string): string {
  return PAIRS.find((p) => p.label === label)?.display ?? label;
}

function SkeletonBar() {
  return <div className="h-10 bg-[#111] animate-pulse" />;
}

function G10SystemicMatrix({
  dollarDominance,
  outlier,
}: {
  dollarDominance: number | null;
  outlier: string | null;
}) {
  return (
    <div className="border border-[#111] bg-[#000000] min-h-[280px] flex flex-col justify-center px-6 py-10">
      <p className="font-mono text-[10px] text-[#666] tracking-widest mb-6 m-0">[ G10 SYSTEMIC MATRIX ]</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div>
          <p className="font-mono text-[9px] text-[#555] tracking-widest m-0 mb-2">DOLLAR DOMINANCE</p>
          <p className="font-mono text-[36px] font-bold text-[#f5f5f5] tabular-nums leading-none m-0">
            {dollarDominance == null ? '—' : `${dollarDominance.toFixed(1)}%`}
          </p>
        </div>
        <div>
          <p className="font-mono text-[9px] text-[#555] tracking-widest m-0 mb-2">OUTLIER</p>
          <p className="font-mono text-[16px] font-bold text-[#f5f5f5] leading-snug m-0 break-words">
            {outlier ?? '—'}
          </p>
        </div>
      </div>
    </div>
  );
}

type HomeLandingBodyProps = {
  initial: GatewayLandingPayload;
  memosSlot: React.ReactNode;
  onAccessTerminal: () => void;
};

export function HomeLandingBody({ initial, memosSlot, onAccessTerminal }: HomeLandingBodyProps) {
  const regimeQ = useLatestRegimeCalls();
  const signalsQ = useLatestSignals();
  const validationQ = useValidationLog(400);
  const lastRunQ = useLastPipelineRun();
  const latestBriefQ = useLatestBrief();
  const pulseQ = useCrossAssetPulse();
  const deskSnapQ = useLatestDeskOpenCardsSnapshot();

  const deskMerged = React.useMemo(() => {
    const live = deskSnapQ.data;
    if (live?.cards?.length) return live;
    return initial.desk;
  }, [deskSnapQ.data, initial.desk]);

  const calls = React.useMemo(() => {
    const live = regimeQ.data;
    if (live && Object.keys(live).length > 0) return live;
    return initial.regime;
  }, [regimeQ.data, initial.regime]);

  const sigs = React.useMemo(() => {
    const live = signalsQ.data;
    if (live && Object.keys(live).length > 0) return live;
    return initial.signals;
  }, [signalsQ.data, initial.signals]);

  const valRows = validationQ.data;

  const regimeErr = regimeQ.isError;
  const sigErr = signalsQ.isError;
  const syncError = regimeErr || sigErr;
  const bootLoading =
    regimeQ.isPending ||
    signalsQ.isPending ||
    (deskSnapQ.isPending && !initial.desk.cards.length);

  const sortedDesk = React.useMemo(() => {
    const rows = deskMerged.cards ?? [];
    return [...rows].sort((a, b) => {
      const ar = a.global_rank ?? 999;
      const br = b.global_rank ?? 999;
      return ar - br;
    });
  }, [deskMerged.cards]);

  const rank1 = sortedDesk[0];
  const rank2 = sortedDesk[1];
  const rank3 = sortedDesk[2];
  const ranksTail = sortedDesk.slice(3);

  const deskAsOf = deskMerged.asOfDate;
  const eurCall = calls?.EURUSD;
  const asOfDay =
    deskAsOf ??
    (lastRunQ.data as string | undefined)?.slice(0, 10) ??
    (eurCall as { date?: string } | undefined)?.date ??
    new Date().toISOString().slice(0, 10);
  const pipelineClock = lastRunQ.data
    ? `${new Date(lastRunQ.data).toISOString().slice(11, 16)} UTC`
    : '—';

  const apexScore = rank1?.apex_score;
  const showHero =
    rank1 != null && apexScore != null && !Number.isNaN(apexScore) && apexScore > 0.4;
  const showSystemicFallback = rank1 != null && !showHero;

  const tableRows = mapValidationLogToTableRows(valRows, 6);
  const acc7 = rolling7dAccuracyPct(valRows ?? []);
  const callsSinceApr = callsValidatedSince(valRows, '2026-04-01');
  const statsLoading = validationQ.isPending;

  const edgePct =
    initial.verifiedEdgePct != null ? initial.verifiedEdgePct.toFixed(1) : null;

  const [universeOpen, setUniverseOpen] = React.useState(false);

  return (
    <main className="flex-1 bg-[#000000] text-[#e8e8e8]">
      <section className="bg-[#000000] text-[#e8e8e8] border-b border-[#111]">
        <div className="w-full px-6 md:px-8 pt-10 pb-12">
          <div className="flex flex-wrap items-center gap-2.5 mb-8">
            <span
              className={`w-1.5 h-1.5 shrink-0 ${
                syncError
                  ? 'bg-[var(--color-bearish)]'
                  : bootLoading
                    ? 'bg-[#737373]'
                    : 'bg-[var(--color-bullish)]'
              }`}
            />
            <span className="font-mono text-[11px] text-[#737373] tracking-widest">
              {syncError
                ? 'OFFLINE · G10 DESK · UNIVERSE'
                : bootLoading
                  ? 'LOADING · G10 DESK · UNIVERSE'
                  : 'SYNCED · G10 DESK · UNIVERSE'}
            </span>
            <span className="font-mono text-[10px] text-[#555] tracking-widest tabular-nums">
              · {asOfDay} {pipelineClock}
            </span>
          </div>

          <div className="min-h-[60vh] flex flex-col justify-center py-8 md:py-12">
            <p className="font-mono text-[9px] tracking-[0.2em] text-[#666] m-0">[ FX REGIME LAB v1.0 ]</p>
            <p className="font-serif text-4xl md:text-6xl text-[#e5e5e5] leading-[1.05] tracking-tight mt-5 mb-0 max-w-5xl">
              Signal, Not Noise. Institutional context for the G10 macro universe.
            </p>
          </div>

          <p className="font-mono text-[10px] text-[#666] tracking-widest mb-8 max-w-xl">
            Anonymous-first gateway. Ranked structural asymmetry, validated ledger, vault terminal.
          </p>

          <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-4 mb-8">
            <div className="min-w-0">
              {bootLoading && !initial.desk.cards.length ? (
                <div className="flex flex-col lg:flex-row gap-4">
                  <div className="lg:flex-[7] min-h-[320px] bg-[#0a0a0a] border border-[#1a1a1a] animate-pulse" />
                  <div className="lg:flex-[3] flex flex-col gap-2">
                    <div className="h-16 bg-[#0a0a0a] border border-[#1a1a1a] animate-pulse" />
                    <div className="h-16 bg-[#0a0a0a] border border-[#1a1a1a] animate-pulse" />
                  </div>
                </div>
              ) : sortedDesk.length === 0 ? (
                <p className="font-mono text-[12px] text-[#888] tracking-wide">No desk open cards for the universe yet.</p>
              ) : (
                <>
                  <div className="flex flex-col lg:flex-row gap-4 items-stretch">
                    <div className="lg:flex-[7] min-w-0 min-h-0">
                      {showSystemicFallback ? (
                        <G10SystemicMatrix
                          dollarDominance={initial.systemic.dollarDominance}
                          outlier={initial.systemic.outlier}
                        />
                      ) : (
                        <DeskCard
                          variant="hero"
                          pairDisplay={pairDisplay(rank1.pair)}
                          spot={sigs?.[rank1.pair]?.spot ?? null}
                          confidence={calls?.[rank1.pair]?.confidence ?? null}
                          rankJump={deskMerged.rankJumpByPair[rank1.pair]}
                          regimeAge={rank1.regime_age}
                          apexScoreDisplay={
                            rank1.apex_score != null ? Math.round(rank1.apex_score * 100) : null
                          }
                          structuralRegime={rank1.structural_regime}
                          invalidationTriggered={rank1.invalidation_triggered}
                          telemetryStatus={rank1.telemetry_status}
                          dominanceArray={rank1.dominance_array}
                          painIndex={rank1.pain_index}
                          markovProbabilities={rank1.markov_probabilities}
                          aiBrief={rank1.ai_brief}
                          telemetryAudit={rank1.telemetry_audit}
                          parameterInstability={rank1.parameter_instability}
                          linkedinCardData={{
                            date: rank1.date,
                            pair: rank1.pair,
                            pair_display: pairDisplay(rank1.pair),
                            pair_slug:
                              PAIRS.find((p) => p.label === rank1.pair)?.urlSlug ??
                              rank1.pair.toLowerCase(),
                            structural_regime: rank1.structural_regime,
                            apex_score: rank1.apex_score,
                            global_rank: rank1.global_rank,
                            regime_age: rank1.regime_age,
                            pain_index: rank1.pain_index,
                            dominance_array: rank1.dominance_array,
                            markov_probabilities: rank1.markov_probabilities,
                            ai_brief: rank1.ai_brief,
                            spot: sigs?.[rank1.pair]?.spot ?? null,
                            confidence: calls?.[rank1.pair]?.confidence ?? null,
                            rank_jump: deskMerged.rankJumpByPair[rank1.pair] ?? null,
                            desk_as_of: asOfDay,
                          }}
                        />
                      )}
                    </div>
                    <div className="lg:flex-[3] min-w-0 flex flex-col gap-2">
                      {showHero
                        ? [rank2, rank3].map((row) =>
                            row ? (
                              <DeskCardTelemetryRow
                                key={row.pair}
                                pairLabel={pairDisplay(row.pair)}
                                spot={sigs?.[row.pair]?.spot ?? null}
                                structuralRegime={row.structural_regime}
                                confidence={calls?.[row.pair]?.confidence ?? null}
                                apexScoreDisplay={
                                  row.apex_score != null ? Math.round(row.apex_score * 100) : null
                                }
                                telemetryAudit={row.telemetry_audit}
                                parameterInstability={row.parameter_instability}
                              />
                            ) : null,
                          )
                        : null}
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => setUniverseOpen((o) => !o)}
                    className="mt-6 font-mono text-[10px] text-[#555] tracking-widest bg-transparent border-0 cursor-pointer underline decoration-[#333] underline-offset-4 hover:text-[#888] hover:decoration-[#555] transition-colors p-0"
                  >
                    {universeOpen ? '[ HIDE UNIVERSE ]' : '[ VIEW ENTIRE UNIVERSE ]'}
                  </button>

                  {universeOpen && ranksTail.length > 0 ? (
                    <div className="mt-4 border border-[#111] bg-[#000000] overflow-x-auto">
                      <table className="w-full font-mono text-[10px] text-[#b0b0b0] border-collapse">
                        <tbody>
                          {ranksTail.map((row) => (
                            <tr key={row.pair} className="border-t border-[#111]">
                              <td className="py-1.5 px-2 text-[#666] tabular-nums w-8">
                                #{row.global_rank ?? '—'}
                              </td>
                              <td className="py-1.5 px-2 text-[#e0e0e0] whitespace-nowrap">{pairDisplay(row.pair)}</td>
                              <td className="py-1.5 px-2 tabular-nums text-right">
                                {sigs?.[row.pair]?.spot != null ? fmt2(sigs[row.pair]!.spot as number) : '—'}
                              </td>
                              <td className="py-1.5 px-2 min-w-[120px] max-w-[200px] truncate">{row.structural_regime}</td>
                              <td className="py-1.5 px-2 tabular-nums text-right w-12">
                                {calls?.[row.pair]?.confidence != null
                                  ? `${Math.round((calls[row.pair]!.confidence as number) * 100)}%`
                                  : '—'}
                              </td>
                              <td className="py-1.5 px-2 tabular-nums text-right text-[#666]">
                                {row.apex_score != null ? (
                                  <span className="tabular-nums">{row.apex_score.toFixed(3)}</span>
                                ) : (
                                  '—'
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : null}
                </>
              )}
            </div>
            <div className="min-w-0">{memosSlot}</div>
          </div>

          <div className="mt-10 flex flex-wrap gap-3 items-center">
            <button
              type="button"
              onClick={onAccessTerminal}
              className="bg-[#f5f5f5] text-[#000000] font-sans font-semibold text-[13px] px-5 py-2.5 transition-[opacity,transform] hover:opacity-90 active:scale-[0.98] border-0 cursor-pointer"
            >
              [ ACCESS TERMINAL ]
            </button>
            <Link
              href="/brief"
              className="text-[#888] font-sans font-medium text-[13px] py-2.5 underline decoration-[#333] underline-offset-4 hover:text-[#ccc] transition-colors"
            >
              Read today&apos;s brief
            </Link>
            <Link
              href="/terminal/performance"
              className="font-mono text-[10px] text-[#555] border border-[#333] px-3 py-2 hover:border-[#555] transition-colors"
            >
              Alpha ledger →
            </Link>
          </div>
        </div>
      </section>

      <div className="border-t border-[#111]" />

      <section className="border-b border-[#111] bg-[#000000]">
        <div className="w-full px-6 md:px-8 grid grid-cols-2 lg:grid-cols-4">
          {[
            { label: 'Pairs tracked', value: '7' },
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
              className={`py-[22px] ${i % 2 === 0 ? 'pr-6 border-r border-[#111]' : 'pl-6'} ${i < 2 ? 'border-b border-[#111] lg:border-b-0' : ''} lg:border-r lg:pr-6 lg:pl-6 ${i === 0 ? 'lg:pl-0' : ''} ${i === 3 ? 'lg:border-r-0' : ''}`}
            >
              {statsLoading ? (
                <SkeletonBar />
              ) : (
                <>
                  <p className="font-mono text-[26px] font-bold text-[#f0f0f0] tracking-tight mb-1 tabular-nums">{s.value}</p>
                  <p className="font-mono text-[10px] text-[#737373] tracking-widest uppercase">{s.label}</p>
                </>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="w-full px-6 md:px-8 pb-12 pt-12 bg-[#000000]">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="border border-[#111] p-5 bg-[#000000]">
            <p className="font-mono text-[10px] text-[#737373] tracking-widest mb-2">GLOBAL SENTIMENT</p>
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'VIX', v: pulseQ.data?.vix.value, c: pulseQ.data?.vix.change },
                { label: 'DXY', v: pulseQ.data?.dxy.value, c: pulseQ.data?.dxy.change },
                { label: 'CRUDE OIL', v: pulseQ.data?.oil.value, c: pulseQ.data?.oil.change },
              ].map((r) => (
                <div key={r.label} className="border border-[#111] p-3 bg-[#000000]">
                  <p className="font-mono text-[9px] text-[#888] tracking-widest mb-1">{r.label}</p>
                  <p className="font-mono text-sm font-bold text-[#e8e8e8] tabular-nums">{fmt2(r.v as number | undefined)}</p>
                  <p className={`font-mono text-[10px] tabular-nums ${r.c != null && r.c >= 0 ? 'text-[#16a34a]' : 'text-[#dc2626]'}`}>
                    {r.c == null ? '—' : `${r.c >= 0 ? '+' : ''}${r.c.toFixed(2)} d/d`}
                  </p>
                </div>
              ))}
            </div>
          </div>
          <div className="border border-[#111] p-5 bg-[#000000]">
            <p className="font-mono text-[10px] text-[#737373] tracking-widest mb-2">LIVE AI SUMMARY</p>
            {latestBriefQ.isPending ? (
              <div className="h-20 bg-[#111] animate-pulse" />
            ) : (
              <p className="font-sans text-[13px] text-[#a3a3a3] leading-relaxed">
                {latestBriefQ.data?.brief_text ?? 'No live global brief has been generated yet.'}
              </p>
            )}
          </div>
        </div>
      </section>

      <section className="w-full px-6 md:px-8 pb-12 bg-[#000000]">
        <div className="flex items-baseline justify-between mb-5">
          <div>
            <h2 className="font-sans font-bold text-xl text-[#f0f0f0] tracking-tight m-0">30-Day Regime View</h2>
            <p className="font-mono text-[11px] text-[#737373] mt-1.5">Cross-pair regime at a glance. Click a pair for detail.</p>
          </div>
        </div>
        <RegimeHeatmap />
      </section>

      <section className="bg-[#000000] border-y border-[#111]">
        <div className="w-full px-6 md:px-8 py-14">
          <div className="flex items-start justify-between mb-7 flex-wrap gap-5">
            <div>
              <p className="font-mono text-[10px] text-[#555] tracking-widest mb-2">VALIDATION LOG</p>
              <h2 className="font-sans font-bold text-xl text-[#f2f2f2] tracking-tight m-0">Next-day outcome, on the record.</h2>
              <p className="font-sans text-[13px] text-[#737373] mt-2">
                Every call validated the following trading day. No revisions, no ex-post edits.
              </p>
            </div>
            <div className="text-right">
              <p className="font-mono text-3xl font-bold text-[var(--color-bullish)] tracking-tight leading-none tabular-nums">
                {acc7 == null ? '—' : `${acc7.toFixed(1)}%`}
              </p>
              <p className="font-mono text-[10px] text-[#555] tracking-widest mt-1">7-DAY ACCURACY</p>
            </div>
          </div>
          {validationQ.isPending ? (
            <div className="h-40 bg-[#111] animate-pulse border border-[#1e1e1e]" />
          ) : validationQ.isError ? (
            <p className="font-mono text-xs text-[var(--color-bearish)]">Validation data unavailable.</p>
          ) : (
            <ValidationTable rows={tableRows} tone="dark" />
          )}
          <Link
            href="/terminal/performance"
            className="inline-block font-mono text-[11px] text-[#737373] bg-transparent border border-[#222] px-4 py-2 mt-4 hover:border-[#444] transition-colors"
          >
            Full validation log →
          </Link>
        </div>
      </section>

      <section className="w-full px-6 md:px-8 py-16 bg-[#000000]">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-16 items-start">
          <div>
            <p className="font-mono text-[10px] text-[#737373] tracking-widest mb-3.5">SIGNAL ARCHITECTURE</p>
            <h2 className="font-sans font-bold text-[28px] text-[#f0f0f0] tracking-tight leading-snug mb-4">
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
          <div className="border border-[#111] bg-[#000000]">
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
              <div key={s.n} className={`flex items-start gap-5 p-5 ${i < 3 ? 'border-b border-[#111]' : ''}`}>
                <span className="font-mono text-[11px] font-bold min-w-[24px] pt-0.5 tabular-nums" style={{ color: s.color }}>
                  {s.n}
                </span>
                <div>
                  <p className="font-sans font-semibold text-sm text-[#e8e8e8] mb-1">{s.label}</p>
                  <p className="font-sans text-[13px] text-[#737373] leading-relaxed">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-[#111] bg-[#000000]">
        <div className="w-full px-6 md:px-8 py-16 md:py-20 flex flex-col gap-8">
          <p className="font-mono text-[9px] tracking-[0.12em] text-[#666] m-0 order-1">
            [ SYSTEM GENESIS: 10-ROUND ADVERSARIAL CRUCIBLE ]
          </p>
          <div className="order-2 flex flex-col gap-4 md:flex-row md:items-end md:justify-between md:gap-8">
            <div>
              <h2 className="font-sans font-bold text-[22px] md:text-[26px] text-[#f0f0f0] tracking-tight m-0">
                Lead Researcher &amp; Founder
              </h2>
              <p className="font-mono text-[11px] text-[#737373] mt-2 m-0">G10 FX · Forward-walking validation · Obsidian desk</p>
            </div>
            <span className="font-mono text-[10px] text-[#a3a3a3] tracking-widest border border-[#333] px-2 py-1.5 tabular-nums self-start md:self-end shrink-0">
              [ VERIFIED 90D EDGE: {edgePct != null ? `${edgePct}%` : '—'} ]
            </span>
          </div>
          <p className="font-sans text-[15px] text-[#a3a3a3] leading-relaxed max-w-[720px] m-0 order-3">
            Research into how G10 FX regimes form and break — rate differentials, COT, volatility, and microstructure. Public trace:
            dated calls, validated outcomes, no narrative added after the fact.
          </p>
          <div className="flex gap-5 flex-wrap order-4">
            <Link
              href="/about"
              className="font-sans text-[13px] font-medium text-[#e8e8e8] bg-transparent border border-[#333] px-4 py-2 hover:border-[#555] transition-all active:scale-[0.98]"
            >
              About this project
            </Link>
            <Link
              href="/brief"
              className="font-sans text-[13px] font-medium text-[#737373] bg-transparent border-none py-2 underline decoration-[#444] underline-offset-4 hover:decoration-[#737373] transition-colors"
            >
              Today&apos;s brief →
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
