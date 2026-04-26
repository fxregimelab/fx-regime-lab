import { HeroRegimeCard } from '@/components/HeroRegimeCard';
import { EmptyState } from '@/components/states';
import { PAIRS } from '@/lib/mock/data';
import { pairTextClass } from '@/lib/pair-styles';
import { defaultSignalRow, mapRegimeCallRow, mapSignalRowWithChange } from '@/lib/supabase/map-row';
import { getLatestRegimeCalls, getLatestSignals } from '@/lib/supabase/queries';
import type { SignalRow } from '@/lib/types';
import Link from 'next/link';

const definitions = [
  {
    n: '01',
    label: 'EURUSD' as const,
    title: 'Rate Differentials',
    text: '2Y sovereign yield spreads anchor the medium-term FX regime. They summarize expected policy divergence in a single number the composite can compare across pairs.',
    sub: 'Widening spreads in favor of the dollar tend to coincide with USD strength regimes until positioning or vol forces a reassessment.',
  },
  {
    n: '02',
    label: 'USDJPY' as const,
    title: 'COT Positioning',
    text: 'CFTC non-commercial positioning is rank-ordered into a percentile so crowded trades read the same for EUR, JPY, and INR.',
    sub: 'Extremes flag reversal risk; alignment with the rate leg adds conviction when the crowd and fundamentals point the same way.',
  },
  {
    n: '03',
    label: 'USDINR' as const,
    title: 'Realized Volatility',
    text: '5d and 20d realized volatility are stacked against 30d implied to detect compression or a vol tax that should slow trend conviction.',
    sub: 'When implied vol spikes through its own historical gate, the system prioritizes a vol-expanding read before directional labels.',
  },
];

export default async function FxRegimePage() {
  const [regimeRes, ...signalResults] = await Promise.all([
    getLatestRegimeCalls(),
    ...PAIRS.map((p) => getLatestSignals(p.label)),
  ]);

  const regimeRows = regimeRes.error ? [] : (regimeRes.data ?? []).map(mapRegimeCallRow);
  const signalByPair: Record<string, SignalRow> = {};
  PAIRS.forEach((p, i) => {
    const sr = signalResults[i];
    signalByPair[p.label] =
      sr && !sr.error && sr.data?.[0] ? mapSignalRowWithChange(sr.data) : defaultSignalRow(p.label, '');
  });

  return (
    <div className="mx-auto max-w-[1280px] px-6 py-10">
      <p className="font-mono text-[10px] tracking-widest text-[#a0a0a0]">FX REGIME</p>
      <h1 className="mt-2 font-sans text-[32px] font-extrabold tracking-tight text-[#0a0a0a]">
        What is an FX Regime?
      </h1>

      <section className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {definitions.map((d) => (
          <div key={d.n} className="border border-[#e5e5e5] p-5">
            <p className={`font-mono text-[28px] font-bold leading-none ${pairTextClass(d.label)}`}>
              {d.n}
            </p>
            <h2 className="mt-3 font-sans text-[16px] font-semibold text-[#0a0a0a]">{d.title}</h2>
            <p className="mt-3 font-sans text-[13px] leading-relaxed text-[#525252]">{d.text}</p>
            <p className="mt-2 font-sans text-[13px] leading-relaxed text-[#737373]">{d.sub}</p>
          </div>
        ))}
      </section>

      <section className="mt-14 border border-[#e5e5e5] p-6">
        <p className="font-mono text-[10px] tracking-widest text-[#a0a0a0]">COMPOSITE SCALE</p>
        <p className="mt-2 font-sans text-[14px] text-[#525252]">
          Normalized signals roll into a single score from about -2 (USD weakness) to +2 (USD
          strength) before the regime label is applied.
        </p>
        <div className="relative mt-8 px-2">
          <div className="h-2 w-full bg-gradient-to-r from-[#D94030] via-[#737373] to-[#4BA3E3]" />
          <div className="mt-3 flex justify-between font-mono text-[9px] text-[#a0a0a0]">
            <span>-2</span>
            <span>-1</span>
            <span>0</span>
            <span>+1</span>
            <span>+2</span>
          </div>
        </div>
      </section>

      <section className="mt-14">
        <h2 className="font-sans text-[18px] font-semibold text-[#0a0a0a]">
          Current regime summary
        </h2>
        {regimeRows.length === 0 ? (
          <div className="mt-6">
            <EmptyState title="No regime calls" subtitle="Pipeline has not run yet." />
          </div>
        ) : (
          <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
            {PAIRS.map((p) => {
              const regime = regimeRows.find((r) => r.pair === p.label);
              if (!regime) return null;
              return (
                <HeroRegimeCard
                  key={p.label}
                  pair={p}
                  regime={regime}
                  signal={signalByPair[p.label] ?? defaultSignalRow(p.label, '')}
                />
              );
            })}
          </div>
        )}
      </section>

      <div className="mt-12">
        <Link
          href="/brief"
          className="inline-flex bg-[#0a0a0a] px-5 py-2.5 font-sans text-[13px] font-semibold text-white"
        >
          Today&apos;s calls →
        </Link>
      </div>
    </div>
  );
}
