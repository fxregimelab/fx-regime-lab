import { ConfidenceBar } from '@/components/ConfidenceBar';
import { RegimeHeatmap } from '@/components/RegimeHeatmap';
import { EmptyState, ErrorBoundaryCard } from '@/components/states';
import { PAIRS, REGIME_HEATMAP_COLORS } from '@/lib/mock/data';
import { pairTextClass } from '@/lib/pair-styles';
import {
  defaultSignalRow,
  mapHeatmapRows,
  mapHistoryRow,
  mapMacroEventRow,
  mapRegimeCallRow,
  mapSignalRow,
  mapSignalRowWithChange,
} from '@/lib/supabase/map-row';
import {
  getLatestRegimeCalls,
  getLatestSignals,
  getRegimeHeatmap,
  getRegimeHistory,
  getUpcomingMacroEvents,
} from '@/lib/supabase/queries';
import { fmt2, fmtChg, fmtInt, fmtSpot } from '@/lib/utils/format';
import Link from 'next/link';
import { notFound } from 'next/navigation';

export function generateStaticParams() {
  return PAIRS.map((p) => ({ pair: p.urlSlug }));
}

export default async function PairDetailPage({
  params,
}: {
  params: Promise<{ pair: string }>;
}) {
  const { pair: pairSlug } = await params;
  const pair = PAIRS.find((p) => p.urlSlug === pairSlug);
  if (!pair) notFound();

  const [regimeRes, sigRes, histRes, eventsRes, heatmapRes] = await Promise.all([
    getLatestRegimeCalls(),
    getLatestSignals(pair.label),
    getRegimeHistory(pair.label),
    getUpcomingMacroEvents(),
    getRegimeHeatmap(),
  ]);

  if (regimeRes.error) {
    return <ErrorBoundaryCard tone="shell" message={regimeRes.error.message} />;
  }

  const regimeRows = (regimeRes.data ?? []).map(mapRegimeCallRow);
  const regime = regimeRows.find((r) => r.pair === pair.label);
  if (!regime) {
    return <EmptyState title="No regime call" subtitle="Pipeline has not run yet." />;
  }

  const rawSignals = sigRes.error ? [] : (sigRes.data ?? []);
  const signalRowsRaw = rawSignals.map(mapSignalRow);
  const signal =
    rawSignals.length > 0
      ? mapSignalRowWithChange(rawSignals)
      : defaultSignalRow(pair.label, regime.date);
  const chg = fmtChg(signal.day_change_pct);

  const history = histRes.error ? [] : (histRes.data ?? []).map(mapHistoryRow);

  const upcoming = eventsRes.error
    ? []
    : (eventsRes.data ?? [])
        .map(mapMacroEventRow)
        .filter((e) => e.pairs.includes(pair.label))
        .slice(0, 4);

  const heatmapData =
    heatmapRes.error || !heatmapRes.data?.length
      ? { dates: [], regimes: {} }
      : mapHeatmapRows(heatmapRes.data as Array<{ date: string; pair: string; regime: string }>);

  const signalRows = [
    { k: 'RATE DIFF 2Y', v: fmt2(signal.rate_diff_2y) },
    { k: 'COT %', v: fmtInt(signal.cot_percentile) },
    { k: 'REAL VOL 20D', v: fmt2(signal.realized_vol_20d) },
    { k: 'REAL VOL 5D', v: fmt2(signal.realized_vol_5d) },
    {
      k: 'IMPLIED VOL 30D',
      v: signal.implied_vol_30d == null ? '—' : fmt2(signal.implied_vol_30d),
    },
  ];

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-10">
      <Link
        href="/brief"
        className="font-mono text-[11px] text-[#737373] underline decoration-[#e5e5e5]"
      >
        ← All pairs
      </Link>
      <div className="mt-6 flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <h1 className={`font-mono text-[20px] font-bold ${pairTextClass(pair.label)}`}>
            {pair.display}
          </h1>
          <div className="mt-2 flex items-baseline gap-3">
            <span className="font-mono text-[18px] text-[#0a0a0a]">
              {fmtSpot(signal.spot, pair.label)}
            </span>
            <span
              className={`font-mono text-[11px] ${chg.dir === 'up' ? 'text-[#16a34a]' : chg.dir === 'down' ? 'text-[#dc2626]' : 'text-[#a0a0a0]'}`}
            >
              {chg.str}
            </span>
          </div>
        </div>
      </div>

      <div className="mt-10 grid gap-8 md:grid-cols-3">
        <div className="md:col-span-2">
          <div className="border border-[#e5e5e5] bg-white p-5">
            <p className="font-sans text-[16px] font-semibold uppercase text-[#0a0a0a]">
              {regime.regime}
            </p>
            <div className="mt-2 max-w-md">
              <ConfidenceBar value={regime.confidence} pairColor={pair.pairColor} />
            </div>
            <p className="mt-4 font-sans text-[12px] text-[#737373]">{regime.primary_driver}</p>
            <p className="mt-2 font-mono text-[11px] text-[#525252]">
              Composite {fmt2(regime.signal_composite)}
            </p>
            <table className="mt-6 w-full border-t border-[#e5e5e5] text-left">
              <tbody>
                {signalRows.map((r) => (
                  <tr key={r.k} className="border-b border-[#f0f0f0]">
                    <td className="py-2 font-mono text-[10px] text-[#a0a0a0]">{r.k}</td>
                    <td className="py-2 text-right font-mono text-[11px] text-[#0a0a0a]">{r.v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div>
          <p className="font-mono text-[10px] tracking-wide text-[#a0a0a0]">UPCOMING</p>
          <ul className="mt-3 space-y-3">
            {upcoming.map((e) => (
              <li key={`${e.date}-${e.event}`} className="border-b border-[#f0f0f0] pb-3">
                <p className="font-mono text-[10px] text-[#737373]">{e.date}</p>
                <p className="font-sans text-[13px] font-semibold text-[#0a0a0a]">{e.event}</p>
                <span
                  className={`mt-1 inline-block font-mono text-[8px] font-semibold uppercase ${
                    e.impact === 'HIGH'
                      ? 'text-[#dc2626]'
                      : e.impact === 'MEDIUM'
                        ? 'text-amber-600'
                        : 'text-[#a0a0a0]'
                  }`}
                >
                  {e.impact}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <section className="mt-12">
        <h2 className="font-mono text-[10px] tracking-wide text-[#a0a0a0]">30-DAY HISTORY</h2>
        <div className="mt-3 overflow-x-auto border border-[#e5e5e5]">
          <table className="w-full text-left">
            <thead className="bg-[#fafafa]">
              <tr>
                {(['DATE', 'REGIME', 'CONF'] as const).map((h) => (
                  <th key={h} className="px-3 py-2 font-mono text-[9px] text-[#a0a0a0]">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {history.map((row, i) => (
                <tr key={row.date} className={i % 2 === 0 ? 'bg-white' : 'bg-[#fafafa]'}>
                  <td className="px-3 py-2 font-mono text-[10px]">{row.date}</td>
                  <td className="px-3 py-2 font-mono text-[10px]">{row.regime}</td>
                  <td className="px-3 py-2 font-mono text-[10px]">
                    {Math.round(row.confidence * 100)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-12">
        <h2 className="font-sans text-[16px] font-semibold text-[#0a0a0a]">
          30-day regime heatmap
        </h2>
        <div className="mt-4">
          {heatmapData.dates.length === 0 ? (
            <p className="font-mono text-[12px] text-[#a0a0a0]">
              Heatmap available after first pipeline run.
            </p>
          ) : (
            <RegimeHeatmap
              data={heatmapData}
              colors={REGIME_HEATMAP_COLORS}
              pairLabels={[pair.label]}
            />
          )}
        </div>
      </section>
    </div>
  );
}
