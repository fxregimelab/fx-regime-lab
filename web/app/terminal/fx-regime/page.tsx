import { ConfidenceBar } from '@/components/ConfidenceBar';
import { RegimeHeatmap } from '@/components/RegimeHeatmap';
import { PAIRS, REGIME_HEATMAP_COLORS } from '@/lib/mock/data';
import { pairTextClass } from '@/lib/pair-styles';
import {
  defaultSignalRow,
  mapHeatmapRows,
  mapRegimeCallRow,
  mapSignalRowWithChange,
} from '@/lib/supabase/map-row';
import { getLatestRegimeCalls, getLatestSignals, getRegimeHeatmap } from '@/lib/supabase/queries';
import type { HeatmapData, RegimeCall, SignalRow } from '@/lib/types';
import { fmt2, fmtInt, fmtSpot } from '@/lib/utils/format';
import Link from 'next/link';

const cardHover: Record<string, string> = {
  EURUSD: 'hover:border-[#4BA3E3]',
  USDJPY: 'hover:border-[#F5923A]',
  USDINR: 'hover:border-[#D94030]',
};

export default async function TerminalStrategyPage() {
  const [regimeRes, heatmapRes, ...signalResults] = await Promise.all([
    getLatestRegimeCalls(),
    getRegimeHeatmap(),
    ...PAIRS.map((p) => getLatestSignals(p.label)),
  ]);

  const regimeRows: RegimeCall[] = regimeRes.error
    ? []
    : (regimeRes.data ?? []).map(mapRegimeCallRow);

  const signalByPair: Record<string, SignalRow> = {};
  PAIRS.forEach((p, i) => {
    const sr = signalResults[i];
    signalByPair[p.label] =
      sr && !sr.error && sr.data?.[0]
        ? mapSignalRowWithChange(sr.data)
        : defaultSignalRow(p.label, '');
  });

  const heatmapData: HeatmapData =
    heatmapRes.error || !heatmapRes.data?.length
      ? { dates: [], regimes: {} }
      : mapHeatmapRows(heatmapRes.data as Array<{ date: string; pair: string; regime: string }>);

  return (
    <div className="mx-auto max-w-[1200px] px-6 py-10">
      <p className="font-mono text-[9px] font-normal tracking-widest text-[#555]">FX REGIME</p>
      <h1 className="mt-1 font-sans text-[32px] font-extrabold leading-tight tracking-tight text-[#e8e8e8] sm:text-[36px]">
        Strategy Overview
      </h1>
      <p className="mt-2 max-w-2xl font-sans text-[15px] font-normal leading-relaxed text-[#555]">
        Three-desk view of current regime calls and a 30-day label heatmap.
      </p>

      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {PAIRS.map((p) => {
          const regime = regimeRows.find((r) => r.pair === p.label);
          const signal = signalByPair[p.label] ?? defaultSignalRow(p.label, '');

          if (!regime) {
            return (
              <div
                key={p.label}
                className={`border border-[#1e1e1e] bg-[#0c0c0c] p-5 font-mono text-[12px] text-[#737373] ${cardHover[p.label]}`}
              >
                No data — run pipeline
              </div>
            );
          }

          return (
            <Link
              key={p.label}
              href={`/terminal/fx-regime/${p.urlSlug}`}
              className={`border border-[#1e1e1e] bg-[#0c0c0c] p-5 transition-colors ${cardHover[p.label]}`}
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className={`font-mono text-[11px] ${pairTextClass(p.label)}`}>
                  {p.display}
                </span>
                <span className="font-mono text-[#e8e8e8]">{fmtSpot(signal.spot, p.label)}</span>
              </div>
              <p className="mt-2 font-sans text-[13px] font-semibold uppercase leading-tight text-[#e8e8e8]">
                {regime.regime}
              </p>
              <div className="mt-2">
                <ConfidenceBar value={regime.confidence} pairColor={p.pairColor} variant="dark" />
              </div>
              <div className="mt-3 flex flex-wrap justify-between gap-x-2 gap-y-1 font-mono text-[9px] text-[#555]">
                <span>comp {fmt2(regime.signal_composite)}</span>
                <span>rd {fmt2(signal.rate_diff_2y)}</span>
                <span>cot {fmtInt(signal.cot_percentile)}</span>
              </div>
            </Link>
          );
        })}
      </div>

      <section className="mt-10">
        <h2 className="font-sans text-[14px] font-semibold uppercase leading-tight text-[#e8e8e8]">
          30-day regime heatmap
        </h2>
        <div className="mt-4 border border-[#1e1e1e] bg-[#0c0c0c] p-6">
          {heatmapData.dates.length === 0 ? (
            <p className="font-mono text-[12px] text-[#555]">
              Heatmap available after first pipeline run.
            </p>
          ) : (
            <RegimeHeatmap data={heatmapData} colors={REGIME_HEATMAP_COLORS} variant="terminal" />
          )}
        </div>
      </section>
    </div>
  );
}
