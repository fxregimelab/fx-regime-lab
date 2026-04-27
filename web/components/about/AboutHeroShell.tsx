import { PAIRS } from '@/lib/mock/data';
import { pairBgClass } from '@/lib/pair-styles';
import Link from 'next/link';

const THIS_IS = [
  'Daily regime calls for G10 pairs',
  'Public validation trail',
  'Composite signal from 4 families',
  'Morning brief before market open',
  'Terminal for dense monitoring',
];

const THIS_IS_NOT = [
  'A SaaS or subscription product',
  'Investment advice',
  'An automated trading system',
  'Generic macro commentary',
];

export function AboutHeroShell() {
  return (
    <section className="mb-16 border-b border-[#e5e5e5] pb-16">
      <div className="grid gap-12 lg:grid-cols-[1fr_2fr] lg:gap-20">
        <div>
          <p className="mb-5 font-mono text-[10px] tracking-[0.12em] text-[#a0a0a0]">ABOUT</p>
          <h1 className="font-sans text-[36px] font-extrabold leading-[1.05] tracking-tight text-[#0a0a0a] sm:text-[40px]">
            A research system.
            <br />
            Public by design.
          </h1>
          <div className="mt-6 flex gap-2">
            {PAIRS.map((p) => (
              <span key={p.label} className={`inline-block h-[3px] w-6 ${pairBgClass(p.label)}`} />
            ))}
          </div>
          <div className="mt-8 flex flex-col gap-2">
            <Link
              href="/brief"
              className="inline-flex bg-[#0a0a0a] px-4 py-2.5 font-sans text-[13px] font-semibold text-white"
            >
              Today&apos;s brief →
            </Link>
            <Link
              href="/terminal"
              className="inline-flex border border-[#e5e5e5] px-4 py-2.5 font-sans text-[13px] font-medium text-[#0a0a0a]"
            >
              Open terminal →
            </Link>
            <Link
              href="/performance"
              className="inline-flex border border-[#e5e5e5] px-4 py-2.5 font-sans text-[13px] font-medium text-[#0a0a0a]"
            >
              Track record →
            </Link>
          </div>
        </div>
        <div>
          <h2 className="font-sans text-[18px] font-bold tracking-tight text-[#0a0a0a]">Shreyash Sakhare</h2>
          <p className="mt-4 font-sans text-[15px] leading-[1.8] text-[#525252]">
            EE undergrad. Studying how G10 FX regimes form and break using rate differentials, COT positioning, and
            volatility. This is a discretionary macro research system that happens to be public — not a learning journal
            in disguise.
          </p>
          <p className="mt-4 font-sans text-[15px] leading-[1.8] text-[#525252]">
            The site is the public trace of that work — dated calls, validated outcomes, no narrative added after the
            fact. Credibility compounds through calendar discipline and honest validation, not marketing.
          </p>
          <div className="mt-8 grid grid-cols-1 gap-px bg-[#e5e5e5] sm:grid-cols-2">
            <div className="bg-white p-5">
              <p className="mb-3 font-mono text-[10px] tracking-[0.1em] text-[#16a34a]">THIS IS</p>
              <ul className="list-none space-y-2 p-0 font-sans text-[13px] leading-[1.8] text-[#525252]">
                {THIS_IS.map((t) => (
                  <li key={t} className="flex gap-2.5">
                    <span className="shrink-0 font-mono text-[11px] text-[#16a34a]">+</span>
                    <span>{t}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-white p-5">
              <p className="mb-3 font-mono text-[10px] tracking-[0.1em] text-[#dc2626]">THIS IS NOT</p>
              <ul className="list-none space-y-2 p-0 font-sans text-[13px] leading-[1.8] text-[#525252]">
                {THIS_IS_NOT.map((t) => (
                  <li key={t} className="flex gap-2.5">
                    <span className="shrink-0 font-mono text-[11px] text-[#dc2626]">−</span>
                    <span>{t}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
