import Link from 'next/link';
import { CompositeSimulator } from './CompositeSimulator';
import { MethodologyTabs } from './MethodologyTabs';
import { SignalAccordion } from './SignalAccordion';

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-[1280px] px-6 py-10">
      <p className="font-mono text-[10px] tracking-widest text-[#a0a0a0]">ABOUT</p>
      <h1 className="mt-2 font-sans text-[32px] font-extrabold tracking-tight text-[#0a0a0a]">
        A research system. Public by design.
      </h1>
      <p className="mt-6 max-w-2xl font-sans text-[15px] leading-relaxed text-[#525252]">
        FX Regime Lab publishes dated G10 regime calls each morning, shows the signals behind them,
        and validates every outcome the next trading day. The goal is a transparent audit trail —
        not a sales pitch.
      </p>

      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          href="/brief"
          className="inline-flex bg-[#0a0a0a] px-5 py-2.5 font-sans text-[13px] font-semibold text-white"
        >
          Today&apos;s brief →
        </Link>
        <Link
          href="/terminal"
          className="inline-flex border border-[#e5e5e5] px-5 py-2.5 font-sans text-[13px] font-medium text-[#0a0a0a]"
        >
          Open terminal →
        </Link>
      </div>

      <section className="mt-16">
        <p className="font-mono text-[10px] tracking-widest text-[#a0a0a0]">METHODOLOGY</p>
        <h2 className="mt-2 font-sans text-[20px] font-semibold text-[#0a0a0a]">How a run moves</h2>
        <div className="mt-6">
          <MethodologyTabs />
        </div>
      </section>

      <section className="mt-16">
        <p className="font-mono text-[10px] tracking-widest text-[#a0a0a0]">SIGNAL ARCHITECTURE</p>
        <h2 className="mt-2 font-sans text-[20px] font-semibold text-[#0a0a0a]">
          What feeds the composite
        </h2>
        <div className="mt-6">
          <SignalAccordion />
        </div>
      </section>

      <section className="mt-16">
        <p className="font-mono text-[10px] tracking-widest text-[#a0a0a0]">COMPOSITE SIMULATOR</p>
        <h2 className="mt-2 font-sans text-[20px] font-semibold text-[#0a0a0a]">Slide the score</h2>
        <div className="mt-6 max-w-xl">
          <CompositeSimulator />
        </div>
      </section>

      <p className="mt-16 font-mono text-[9px] leading-relaxed text-[#ccc]">
        All outputs are for research and education. Nothing here is investment advice or an offer to
        transact. Past validation does not guarantee future accuracy.
      </p>
    </div>
  );
}
