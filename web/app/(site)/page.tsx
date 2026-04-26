import { HeroRegimeCard } from '@/components/HeroRegimeCard';
import { PairCard } from '@/components/PairCard';
import { RegimeHeatmap } from '@/components/RegimeHeatmap';
import { EmptyState } from '@/components/states';
import { ErrorBoundaryCard } from '@/components/states';
import { PAIRS, REGIME_HEATMAP_COLORS } from '@/lib/mock/data';
import {
  defaultSignalRow,
  mapHeatmapRows,
  mapRegimeCallRow,
  mapSignalRow,
} from '@/lib/supabase/map-row';
import {
  getLatestRegimeCalls,
  getLatestSignals,
  getRegimeHeatmap,
  getValidationStats,
} from '@/lib/supabase/queries';
import type { HeatmapData, PairMeta, RegimeCall, SignalRow } from '@/lib/types';
import Link from 'next/link';

function regimeForPair(rows: RegimeCall[], label: string): RegimeCall | undefined {
  return rows.find((r) => r.pair === label);
}

export default async function HomePage() {
  const [regimeRes, heatmapRes, statsRes] = await Promise.all([
    getLatestRegimeCalls(),
    getRegimeHeatmap(),
    getValidationStats(),
  ]);
  if (regimeRes.error) {
    return (
      <div className="bg-white px-6 py-10">
        <ErrorBoundaryCard message={regimeRes.error.message} tone="shell" />
      </div>
    );
  }

  const regimeRows = (regimeRes.data ?? []).map(mapRegimeCallRow);
  const stats = statsRes.data ?? {
    winRate: 0,
    callsMade: 0,
    medianReturn: 0,
    daysLive: 0,
  };
  const heatmapData: HeatmapData =
    heatmapRes.error || !heatmapRes.data?.length
      ? { dates: [], regimes: {} }
      : mapHeatmapRows(heatmapRes.data as Array<{ date: string; pair: string; regime: string }>);
  if (regimeRows.length === 0) {
    return (
      <div className="bg-white px-6 py-10">
        <EmptyState
          title="No regime calls"
          subtitle="Pipeline has not published regime data yet. Check back after the next run."
        />
      </div>
    );
  }

  const signalPairs = await Promise.all(PAIRS.map((p) => getLatestSignals(p.label)));

  const signalByLabel: Record<PairMeta['label'], SignalRow> = {
    EURUSD: defaultSignalRow('EURUSD', ''),
    USDJPY: defaultSignalRow('USDJPY', ''),
    USDINR: defaultSignalRow('USDINR', ''),
  };

  for (let i = 0; i < PAIRS.length; i++) {
    const p = PAIRS[i];
    const sr = signalPairs[i];
    if (!sr.error && sr.data?.[0]) {
      signalByLabel[p.label] = mapSignalRow(sr.data[0]);
    } else if (!sr.error && sr.data?.[0] === undefined) {
      const r = regimeForPair(regimeRows, p.label);
      signalByLabel[p.label] = defaultSignalRow(p.label, r?.date ?? '');
    }
  }

  const heroPair = PAIRS[0];
  const heroRegime = regimeForPair(regimeRows, heroPair.label);
  const heroSignal = signalByLabel[heroPair.label];
  if (!heroRegime) {
    return (
      <div className="bg-white px-6 py-10">
        <EmptyState title="Incomplete data" subtitle="Expected regime rows for tracked pairs." />
      </div>
    );
  }

  return (
    <div className="bg-white">
      <section className="mx-auto max-w-[1280px] px-6 py-12 md:py-16">
        <div className="grid gap-10 lg:grid-cols-2 lg:items-start lg:gap-16">
          <div>
            <h1 className="font-sans text-[40px] font-extrabold leading-tight tracking-tight text-[#0a0a0a] sm:text-[52px] sm:leading-tight">
              The FX regime call. Dated and on the record.
            </h1>
            <p className="mt-5 max-w-xl font-sans text-[16px] leading-relaxed text-[#525252]">
              G10 FX regime classification across EUR/USD, USD/JPY, and USD/INR. Composite signal
              from rate differentials, COT positioning, and realized volatility. Every call is
              public before the open; every outcome is validated.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/brief"
                className="inline-flex items-center bg-[#0a0a0a] px-5 py-2.5 font-sans text-[13px] font-semibold text-white"
              >
                Read today&apos;s brief →
              </Link>
              <Link
                href="/terminal"
                className="inline-flex items-center border border-[#e5e5e5] bg-white px-5 py-2.5 font-sans text-[13px] font-medium text-[#0a0a0a]"
              >
                Open terminal →
              </Link>
            </div>
          </div>
          <HeroRegimeCard pair={heroPair} regime={heroRegime} signal={heroSignal} />
        </div>
      </section>

      <section className="border-y border-[#e5e5e5] py-6">
        <div className="mx-auto grid max-w-[1280px] grid-cols-2 gap-6 px-6 sm:grid-cols-4">
          {[
            {
              label: 'CALLS MADE',
              value: stats.callsMade > 0 ? String(stats.callsMade) : '—',
            },
            {
              label: 'WIN RATE',
              value: stats.callsMade > 0 ? `${Math.round(stats.winRate * 100)}%` : '—',
            },
            { label: 'PAIRS TRACKED', value: '3' },
            {
              label: 'DAYS LIVE',
              value: stats.daysLive > 0 ? String(stats.daysLive) : '—',
            },
          ].map((s) => (
            <div key={s.label}>
              <p className="font-mono text-[11px] tracking-widest text-[#a0a0a0]">{s.label}</p>
              <p className="mt-1 font-mono text-[22px] font-semibold text-[#0a0a0a]">{s.value}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-[1280px] px-6 py-12">
        <h2 className="font-sans text-[18px] font-semibold text-[#0a0a0a]">Live snapshot</h2>
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {PAIRS.map((p) => {
            const regime = regimeForPair(regimeRows, p.label);
            const signal = signalByLabel[p.label];
            if (!regime) {
              return (
                <div
                  key={p.label}
                  className="border border-[#e5e5e5] bg-[#fafafa] p-4 font-mono text-[12px] text-[#737373]"
                >
                  No regime row for {p.label}
                </div>
              );
            }
            return <PairCard key={p.label} pair={p} regime={regime} signal={signal} />;
          })}
        </div>
      </section>

      <section className="mx-auto max-w-[1280px] px-6 pb-16">
        <h2 className="font-sans text-[18px] font-semibold text-[#0a0a0a]">30-Day Regime Map</h2>
        <p className="mt-1 font-sans text-[13px] text-[#737373]">Regime cell per trading day.</p>
        <div className="mt-6">
          {heatmapData.dates.length === 0 ? (
            <p className="font-mono text-[12px] text-[#a0a0a0]">
              Heatmap available after first pipeline run.
            </p>
          ) : (
            <>
              <p className="mt-2 font-mono text-[9px] text-[#a0a0a0] sm:hidden">Scroll →</p>
              <RegimeHeatmap data={heatmapData} colors={REGIME_HEATMAP_COLORS} />
            </>
          )}
        </div>
      </section>
    </div>
  );
}
