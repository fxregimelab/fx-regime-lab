'use client';

import { useEffect, useMemo } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';
import { useParams } from 'next/navigation';
import { DeskCard } from '@/components/ui/desk-card';
import { WeeklyThesisHud } from '@/components/ui/weekly-thesis-hud';
import { PAIRS } from '@/lib/mockData';
import { fmtPct, fmtChg } from '@/components/ui/utils';
import {
  useDeskOpenCard,
  useTelemetryStatus,
  useSignalHistory,
  useLastPipelineRun,
  useRegimeHistory30D,
  useLatestRegimeCalls,
  useResearchMemosList,
} from '@/lib/queries';
import { isSameWeekUtc, parseThesisBulletsFromJson } from '@/lib/research-memo-thesis';
import { useLocalSettings } from '@/hooks/useLocalSettings';

const TradingViewChart = dynamic(() => import('@/components/ui/trading-view-chart'), {
  ssr: false,
  loading: () => <p className="font-mono text-[11px] text-[#444]">[ Loading TradingView Container... ]</p>,
});

export default function PairDeskPage() {
  const params = useParams();
  const pairSlug = params.pair as string;
  const pair = PAIRS.find((p) => p.urlSlug === pairSlug) ?? PAIRS[0];

  const deskCardQ = useDeskOpenCard(pair.label);
  const telemetryQ = useTelemetryStatus(pair.label);
  const sigHistQ = useSignalHistory(pair.label, 365);
  const regime30Q = useRegimeHistory30D(pair.label);
  const lastRunQ = useLastPipelineRun();
  const regimeLatestQ = useLatestRegimeCalls();
  const memosQ = useResearchMemosList();
  const { chartRange, setSettings, hydrated: settingsHydrated } = useLocalSettings();

  const card = deskCardQ.data;
  const telemetry = telemetryQ.data;
  const sig = sigHistQ.data?.[sigHistQ.data.length - 1];
  const chgObj = fmtChg(sig?.day_change_pct as number | undefined);
  const today =
    lastRunQ.data?.slice(0, 10) ??
    card?.date ??
    new Date().toISOString().slice(0, 10);

  const isOffline = telemetry?.telemetry_status === 'OFFLINE';
  const isCrisis = Boolean(telemetry?.invalidation_triggered) && !isOffline;
  const bodyTone = isOffline ? 'text-[#666]' : 'text-[#e8e8e8]';
  const borderTone = isCrisis ? 'border-[#f59e0b]' : 'border-[#111]';
  const dominanceArray = useMemo(() => card?.dominance_array ?? [], [card?.dominance_array]);
  const topDominance = dominanceArray[0];
  const liveConf = regimeLatestQ.data?.[pair.label]?.confidence;
  const confNum = liveConf != null ? Number(liveConf) : null;

  const latestMemo = memosQ.data?.[0];
  const weeklyThesisBullets = useMemo(() => {
    if (!latestMemo || !isSameWeekUtc(latestMemo.date, today)) return [];
    const bullets = parseThesisBulletsFromJson(latestMemo.ai_thesis_summary);
    return bullets.length === 5 ? bullets : [];
  }, [latestMemo, today]);

  useEffect(() => {
    if (!settingsHydrated) return;
    setSettings({ selectedPair: pair.label });
  }, [settingsHydrated, pair.label, setSettings]);

  const linkedinCardData =
    card && !isOffline
      ? {
          date: card.date,
          pair: pair.label,
          pair_display: pair.display,
          pair_slug: pair.urlSlug,
          structural_regime: card.structural_regime,
          apex_score: card.apex_score,
          global_rank: card.global_rank,
          regime_age: card.regime_age,
          pain_index: card.pain_index,
          dominance_array: card.dominance_array,
          markov_probabilities: card.markov_probabilities,
          ai_brief: card.ai_brief,
          spot: sig?.spot ?? null,
          confidence: confNum,
          pipeline_as_of: today,
        }
      : null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.35 }}
      className={`min-h-screen bg-[#000000] ${bodyTone}`}
    >
      <div
        className="grid grid-cols-1 xl:grid-cols-[72px_minmax(0,1fr)_340px] min-w-0 overflow-hidden"
        style={{
          marginTop: 'var(--terminal-nav-h, 104px)',
          height: 'calc(100dvh - var(--terminal-nav-h, 104px))',
        }}
      >
        <aside className="hidden xl:flex min-h-0 flex-col border-r border-[#111] bg-[#000000] overflow-y-auto">
          <div className="flex-1 py-4">
            {PAIRS.map((p) => {
              const active = p.urlSlug === pairSlug;
              const pairSig = p.label === pair.label ? sig : undefined;
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

        <main className="min-h-0 min-w-0 border-r border-[#111] bg-[#000000] overflow-y-auto">
          <section className={`border-b ${borderTone} px-6 py-5`}>
            <div className="flex items-center justify-between mb-2">
              <p className="font-mono text-[9px] text-[#666] tracking-widest">{pair.display}</p>
              <span className="font-mono text-[9px] font-bold text-[#d4d4d4] tracking-widest border border-[#111] bg-[#000000] px-2 py-1">
                [ PIPELINE VERIFIED ]
              </span>
            </div>
            {isOffline ? (
              <p className="font-mono text-[11px] tracking-widest text-[#8a8a8a] mb-2">
                [ TELEMETRY OFFLINE ]
              </p>
            ) : null}
            {isCrisis ? (
              <p className="font-mono text-[11px] tracking-widest text-[#f59e0b] mb-2">
                [ OVERNIGHT INVALIDATION TRIGGERED ]
              </p>
            ) : null}
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <h1 className="font-mono text-6xl leading-none font-bold text-white tabular-nums">
                  {sig?.spot != null ? Number(sig.spot).toFixed(pair.label === 'USDJPY' ? 2 : 4) : '--'}
                </h1>
                <p className={`font-mono text-[12px] tabular-nums mt-2 ${chgObj.color}`}>{chgObj.str}</p>
              </div>
              <div className="text-right">
                <p className="font-mono text-[9px] text-[#666] tracking-widest">ACTIVE REGIME</p>
                <p
                  className={`font-mono text-[22px] font-extrabold text-[#ffffff] mt-1 tabular-nums ${
                    isCrisis ? 'line-through' : ''
                  }`}
                >
                  {card?.structural_regime ?? '—'}
                </p>
                <p className="font-mono text-[9px] text-[#9b9b9b] mt-1 tracking-widest">CONFIDENCE</p>
                <p className="font-mono text-[14px] text-[#ffffff] font-extrabold mt-1 tabular-nums">
                  {fmtPct(confNum ?? undefined)}
                </p>
                <p className="font-mono text-[9px] text-[#555] mt-1 tracking-widest tabular-nums">{today}</p>
              </div>
            </div>
          </section>

          <section className="grid grid-cols-1 lg:grid-cols-2 border-b border-[#111]">
            <div className="p-4 border-r border-[#111]">
              <p className="font-mono text-[9px] tracking-widest text-[#777] mb-2">
                DOMINANCE MASONRY
              </p>
              <div className="grid grid-cols-2 gap-2">
                <div className="col-span-2 border border-[#1a1a1a] p-3">
                  <p className="font-mono text-[9px] text-[#777]">RANK #1 (50% width)</p>
                  <p className="font-mono text-[12px] text-[#f2f2f2] mt-1">
                    {topDominance
                      ? `${topDominance.signal_family.toUpperCase()} / ${topDominance.dominance_score.toFixed(3)}`
                      : 'N/A'}
                  </p>
                </div>
                {dominanceArray.slice(1).map((item) => (
                  <div key={`${item.rank}-${item.signal_family}`} className="border border-[#151515] p-2">
                    <p className="font-mono text-[10px] text-[#cdcdcd]">
                      #{item.rank} {item.signal_family.toUpperCase()}
                    </p>
                  </div>
                ))}
              </div>
            </div>
            <div className="p-4">
              <p className="font-mono text-[9px] tracking-widest text-[#777] mb-2">MARKOV FOCUS</p>
              <p className="font-mono text-[11px] text-[#dfdfdf]">
                CONTINUATION:{' '}
                {card?.markov_probabilities?.continuation_probability != null
                  ? `${card.markov_probabilities.continuation_probability.toFixed(2)}%`
                  : 'N/A'}
              </p>
              <div className="mt-2 space-y-1">
                {Object.entries(card?.markov_probabilities?.transitions ?? {}).map(
                  ([regime, value]) => (
                    <p key={regime} className="font-mono text-[10px] text-[#8f8f8f]">
                      {regime}: {Number(value).toFixed(2)}%
                    </p>
                  ),
                )}
              </div>
            </div>
          </section>

          <section className="px-6 py-5">
            <div className="h-[560px] bg-[#000000] flex items-center justify-center relative rounded-none">
              <div className="absolute top-3 left-3 font-mono text-[10px] text-[#666] tracking-widest">CHART CONTAINER</div>
              <div className="absolute inset-0">
                <TradingViewChart
                  pairLabel={pair.label}
                  data={sigHistQ.data}
                  regimeData={regime30Q.data}
                  color={pair.pairColor}
                  chartRange={settingsHydrated ? chartRange : '1Y'}
                  onChartRangeChange={(r) => setSettings({ chartRange: r })}
                />
              </div>
            </div>
          </section>
        </main>

        <aside className="flex min-h-0 min-w-0 flex-col gap-4 overflow-y-auto bg-[#000000] px-5 py-5">
          <div className="shrink-0">
            <DeskCard
              variant="hero"
              pairDisplay={pair.display}
              spot={sig?.spot != null ? Number(sig.spot) : null}
              confidence={confNum}
              rankJump={undefined}
              structuralRegime={card?.structural_regime ?? 'N/A'}
              invalidationTriggered={Boolean(telemetry?.invalidation_triggered)}
              telemetryStatus={telemetry?.telemetry_status ?? 'ONLINE'}
              dominanceArray={card?.dominance_array ?? []}
              painIndex={card?.pain_index ?? null}
              markovProbabilities={card?.markov_probabilities ?? null}
              aiBrief={card?.ai_brief ?? null}
              telemetryAudit={card?.telemetry_audit ?? null}
              parameterInstability={card?.parameter_instability ?? false}
              regimeAge={card?.regime_age ?? null}
              apexScoreDisplay={
                card?.apex_score != null ? Math.round(card.apex_score * 100) : null
              }
              linkedinCardData={linkedinCardData}
            />
          </div>
          <WeeklyThesisHud bullets={weeklyThesisBullets} />
        </aside>
      </div>
    </motion.div>
  );
}
