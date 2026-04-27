import Link from 'next/link';

const ROWS: { n: string; label: string; desc: string; colorClass: string }[] = [
  {
    n: '01',
    label: 'Rate Differentials',
    desc: '2Y sovereign yield spreads. Primary driver of medium-term FX regime direction.',
    colorClass: 'text-[#4BA3E3]',
  },
  {
    n: '02',
    label: 'COT Positioning',
    desc: 'CFTC weekly non-commercial net positions as percentile ranks. Crowd and reversal signals.',
    colorClass: 'text-[#F5923A]',
  },
  {
    n: '03',
    label: 'Realized Volatility',
    desc: '5d and 20d realized vs 30d implied. Vol gate forces VOL_EXPANDING above 90th pctile.',
    colorClass: 'text-[#D94030]',
  },
  {
    n: '04',
    label: 'OI and Risk Reversals',
    desc: 'Open interest flows and 25-delta risk reversals. INR-specific series included.',
    colorClass: 'text-[#888888]',
  },
];

export function HomeSignalArchitecture() {
  return (
    <section className="mx-auto max-w-[1280px] px-6 py-16">
      <div className="grid gap-12 lg:grid-cols-[1fr_2fr] lg:items-start">
        <div>
          <p className="mb-3 font-mono text-[10px] tracking-[0.12em] text-[#a0a0a0]">SIGNAL ARCHITECTURE</p>
          <h2 className="font-sans text-[28px] font-bold leading-tight tracking-tight text-[#0a0a0a]">
            Four signal
            <br />
            families. One
            <br />
            composite.
          </h2>
          <p className="mt-4 font-sans text-[14px] leading-relaxed text-[#737373]">
            Each family is normalized to a percentile rank before weighting. The composite drives the regime
            label.
          </p>
        </div>
        <div className="border border-[#e5e5e5]">
          {ROWS.map((s, i) => (
            <div
              key={s.n}
              className={`flex items-start gap-5 px-5 py-5 ${i < 3 ? 'border-b border-[#e5e5e5]' : ''}`}
            >
              <span className={`min-w-[28px] shrink-0 pt-0.5 font-mono text-[11px] font-bold ${s.colorClass}`}>
                {s.n}
              </span>
              <div>
                <p className="font-sans text-[14px] font-semibold text-[#0a0a0a]">{s.label}</p>
                <p className="mt-1 font-sans text-[13px] leading-relaxed text-[#737373]">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="mt-10 text-center">
        <Link href="/about" className="font-sans text-[13px] font-medium text-[#737373] underline decoration-[#d0d0d0] underline-offset-4">
          About this project →
        </Link>
      </div>
    </section>
  );
}
