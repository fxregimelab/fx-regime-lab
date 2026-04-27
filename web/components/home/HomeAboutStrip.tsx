import Link from 'next/link';

export function HomeAboutStrip() {
  return (
    <section className="border-y border-[#e5e5e5] bg-white">
      <div className="mx-auto grid max-w-[1280px] gap-12 px-6 py-12 lg:grid-cols-[1fr_2fr] lg:items-start">
        <div>
          <p className="mb-3 font-mono text-[10px] tracking-[0.12em] text-[#a0a0a0]">ABOUT</p>
          <h2 className="font-sans text-[22px] font-bold tracking-tight text-[#0a0a0a]">Shreyash Sakhare</h2>
          <p className="mt-2 font-mono text-[11px] text-[#a0a0a0]">EE Undergrad · Discretionary Macro Research</p>
        </div>
        <div>
          <p className="mb-5 max-w-xl font-sans text-[15px] leading-relaxed text-[#525252]">
            Studying how G10 FX regimes form and break using rate differentials, COT positioning, and volatility.
            This site is the public trace of that work — dated calls, validated outcomes, no narrative added after
            the fact.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/about"
              className="inline-flex border border-[#e5e5e5] px-4 py-2 font-sans text-[13px] font-medium text-[#0a0a0a] hover:bg-[#fafafa]"
            >
              About this project
            </Link>
            <Link
              href="/brief"
              className="inline-flex font-sans text-[13px] font-medium text-[#737373] underline decoration-[#d0d0d0] underline-offset-4"
            >
              Today&apos;s brief →
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
