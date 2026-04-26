import { ConfidenceBar } from '@/components/ConfidenceBar';
import { PAIRS } from '@/lib/mock/data';
import { pairTextClass } from '@/lib/pair-styles';
import { defaultSignalRow, mapRegimeCallRow, mapSignalRow } from '@/lib/supabase/map-row';
import { getLastPipelineRun, getLatestRegimeCalls, getLatestSignals } from '@/lib/supabase/queries';
import type { RegimeCall, SignalRow } from '@/lib/types';
import { fmt2, fmtInt, fmtSpot } from '@/lib/utils/format';
import Link from 'next/link';

const cardHover: Record<string, string> = {
  EURUSD: 'hover:border-[#4BA3E3]',
  USDJPY: 'hover:border-[#F5923A]',
  USDINR: 'hover:border-[#D94030]',
};

export default async function TerminalIndexPage() {
  const [regimeRes, lastRunRes, ...signalResults] = await Promise.all([
    getLatestRegimeCalls(),
    getLastPipelineRun(),
    ...PAIRS.map((p) => getLatestSignals(p.label)),
  ]);

  const regimeRows: RegimeCall[] = regimeRes.error
    ? []
    : (regimeRes.data ?? []).map(mapRegimeCallRow);

  const signalByPair: Record<string, SignalRow> = {};
  PAIRS.forEach((p, i) => {
    const sr = signalResults[i];
    signalByPair[p.label] =
      sr && !sr.error && sr.data?.[0] ? mapSignalRow(sr.data[0]) : defaultSignalRow(p.label, '');
  });

  const lastRunTs =
    lastRunRes.error || !lastRunRes.data?.[0] ? null : (lastRunRes.data[0].created_at ?? null);
  const lastRunStr = lastRunTs
    ? `${new Date(lastRunTs).toISOString().slice(0, 16).replace('T', ' ')} UTC`
    : 'No run yet';

  return (
    <div className="mx-auto max-w-[900px] px-6 py-12">
      <p className="font-mono text-[9px] font-normal tracking-widest text-[#555]">TERMINAL</p>
      <h1 className="mt-1 font-sans text-[40px] font-extrabold leading-none tracking-tight text-[#e8e8e8]">
        FX Regime Terminal
      </h1>
      <p className="mt-3 max-w-xl font-sans text-[15px] font-normal leading-relaxed text-[#555]">
        A compact desk for regime calls, signal strips, and macro context — three pairs, one layout.
        Data is read from Supabase after each pipeline run.
      </p>

      <div className="mt-10 grid grid-cols-1 gap-3 sm:grid-cols-3">
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

      <div className="mt-8 border border-[#1e1e1e] bg-[#0c0c0c] p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-[#16a34a]" aria-hidden />
            <span className="font-mono text-[9px] text-[#16a34a]">PIPELINE ONLINE</span>
          </div>
          <p className="font-mono text-[9px] text-[#555]">LAST RUN: {lastRunStr}</p>
        </div>
      </div>
    </div>
  );
}
