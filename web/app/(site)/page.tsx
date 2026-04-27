import { HomeAboutStrip } from '@/components/home/HomeAboutStrip';
import { HomeSignalArchitecture } from '@/components/home/HomeSignalArchitecture';
import { HomeValidationStrip } from '@/components/home/HomeValidationStrip';
import { HeroRegimeCard } from '@/components/HeroRegimeCard';
import { PairCard } from '@/components/PairCard';
import { RegimeHeatmap } from '@/components/RegimeHeatmap';
import { EmptyState } from '@/components/states';
import { ErrorBoundaryCard } from '@/components/states';
import { PAIRS, REGIME_HEATMAP_COLORS } from '@/lib/mock/data';
import { pairTopShellClass } from '@/lib/pair-styles';
import {
  defaultSignalRow,
  mapHeatmapRows,
  mapRegimeCallRow,
  mapSignalRowWithChange,
} from '@/lib/supabase/map-row';
import {
  getHomepageKpis,
  getLastPipelineRun,
  getLatestRegimeCalls,
  getLatestSignals,
  getRegimeHeatmap,
  getValidationLog,
} from '@/lib/supabase/queries';
import type { HeatmapData, PairMeta, RegimeCall, SignalRow } from '@/lib/types';
import Link from 'next/link';

function regimeForPair(rows: RegimeCall[], label: string): RegimeCall | undefined {
  return rows.find((r) => r.pair === label);
}

function pipelineStripLine(createdAt: string | null | undefined): string {
  if (!createdAt) return 'PIPELINE · awaiting first run';
  const d = new Date(createdAt);
  const dateStr = d.toISOString().slice(0, 10);
  const timeStr = d.toISOString().slice(11, 16);
  return `PIPELINE · ${dateStr} ${timeStr} UTC · 3 pairs updated`;
}

function snapshotUpdated(createdAt: string | null | undefined): string {
  if (!createdAt) return 'Updated —';
  const d = new Date(createdAt);
  return `${d.toISOString().slice(0, 10)} · Updated ${d.toISOString().slice(11, 16)} UTC`;
}

export default async function HomePage() {
  const [regimeRes, heatmapRes, kpiRes, valSliceRes, lastRunRes] = await Promise.all([
    getLatestRegimeCalls(),
    getRegimeHeatmap(),
    getHomepageKpis(),
    getValidationLog(8),
    getLastPipelineRun(),
  ]);
  if (regimeRes.error) {
    return (
      <div className="bg-white px-6 py-10">
        <ErrorBoundaryCard message={regimeRes.error.message} tone="shell" />
      </div>
    );
  }

  const regimeRows = (regimeRes.data ?? []).map(mapRegimeCallRow);
  const kpis = kpiRes.data ?? {
    pairsTracked: PAIRS.length,
    callsSinceApril2026: 0,
    accuracy7dPct: null,
    signalFamilies: 4,
  };
  const lastCreated = lastRunRes.data?.[0]?.created_at;
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
      signalByLabel[p.label] = mapSignalRowWithChange(sr.data);
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

  const valRowsRaw = valSliceRes.error ? [] : (valSliceRes.data ?? []);

  return (
    <div className="bg-white">
      <section className="mx-auto max-w-[1280px] px-6 py-12 md:py-16">
        <div className="grid gap-10 lg:grid-cols-2 lg:items-start lg:gap-16">
          <div>
            <div className="mb-6 flex items-center gap-2.5">
              <span className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-[#22c55e]" />
              <span className="font-mono text-[11px] tracking-[0.1em] text-[#737373]">
                LIVE · G10 FX · DAILY CALLS
              </span>
            </div>
            <h1 className="font-sans text-[40px] font-extrabold leading-tight tracking-tight text-[#0a0a0a] sm:text-[52px] sm:leading-tight">
              Daily regime calls.
              <br />
              On the record.
            </h1>
            <p className="mt-5 max-w-xl font-sans text-[16px] leading-relaxed text-[#525252]">
              G10 FX regime classification across EUR/USD, USD/JPY, and USD/INR. Composite signal from rate
              differentials, COT positioning, realized volatility, and open-interest skew. Every call is public
              before the open; every outcome is validated.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/brief"
                className="inline-flex items-center bg-[#0a0a0a] px-5 py-2.5 font-sans text-[13px] font-semibold text-white"
              >
                Read today&apos;s brief
              </Link>
              <Link
                href="/performance"
                className="inline-flex items-center border border-[#e5e5e5] bg-white px-5 py-2.5 font-sans text-[13px] font-medium text-[#0a0a0a]"
              >
                Validation log →
              </Link>
            </div>
            <p className="mt-4 font-mono text-[10px] tracking-[0.06em] text-[#a0a0a0]">
              {pipelineStripLine(lastCreated)}
            </p>
          </div>
          <HeroRegimeCard pair={heroPair} regime={heroRegime} signal={heroSignal} />
        </div>
      </section>

      <section className="border-y border-[#e5e5e5]">
        <div className="mx-auto grid max-w-[1280px] grid-cols-2 sm:grid-cols-4">
          {[
            {
              label: 'PAIRS TRACKED',
              value: String(kpis.pairsTracked),
            },
            {
              label: 'CALLS SINCE APR 2026',
              value: kpis.callsSinceApril2026 > 0 ? String(kpis.callsSinceApril2026) : '—',
            },
            {
              label: '7-DAY ACCURACY',
              value:
                kpis.accuracy7dPct != null
                  ? `${kpis.accuracy7dPct >= 10 ? kpis.accuracy7dPct.toFixed(1) : kpis.accuracy7dPct.toFixed(2)}%`
                  : '—',
            },
            {
              label: 'SIGNAL FAMILIES',
              value: String(kpis.signalFamilies),
            },
          ].map((s, i) => (
            <div
              key={s.label}
              className={`px-6 py-5 ${i < 3 ? (i === 1 ? 'sm:border-r sm:border-[#e5e5e5]' : 'border-r border-[#e5e5e5]') : ''}`}
            >
              <p className="font-mono text-[24px] font-bold leading-none tracking-[-0.03em] text-[#0a0a0a]">
                {s.value}
              </p>
              <p className="mt-1.5 font-mono text-[10px] tracking-[0.08em] text-[#a0a0a0]">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      <HomeValidationStrip rows={valRowsRaw} rolling7dPct={kpis.accuracy7dPct} />

      <section className="mx-auto max-w-[1280px] px-6 py-12">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="font-sans text-[18px] font-semibold text-[#0a0a0a]">Live Regime Snapshot</h2>
            <p className="mt-1 font-mono text-[11px] text-[#737373]">{snapshotUpdated(lastCreated)}</p>
          </div>
          <Link
            href="/terminal"
            className="inline-flex items-center border border-[#e5e5e5] bg-white px-4 py-2 font-mono text-[11px] text-[#0a0a0a] hover:bg-[#fafafa]"
          >
            Open terminal →
          </Link>
        </div>
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {PAIRS.map((p) => {
            const regime = regimeForPair(regimeRows, p.label);
            const signal = signalByLabel[p.label];
            if (!regime) {
              return (
                <div key={p.label} className={`border border-[#e5e5e5] p-4 ${pairTopShellClass(p.label)}`}>
                  <EmptyState
                    title={`No data for ${p.display}`}
                    subtitle="Pipeline has not published a regime call for this pair yet."
                  />
                </div>
              );
            }
            return <PairCard key={p.label} pair={p} regime={regime} signal={signal} />;
          })}
        </div>
      </section>

      <section className="mx-auto max-w-[1280px] px-6 pb-16">
        <h2 className="font-sans text-[18px] font-semibold text-[#0a0a0a]">30-Day Regime View</h2>
        <p className="mt-1 font-sans text-[13px] text-[#737373]">One regime cell per pair per trading day.</p>
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

      <HomeSignalArchitecture />
      <HomeAboutStrip />
    </div>
  );
}
