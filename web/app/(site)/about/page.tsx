import { AboutHeroShell } from '@/components/about/AboutHeroShell';
import Link from 'next/link';
import { CompositeSimulator } from './CompositeSimulator';
import { MethodologyTabs } from './MethodologyTabs';
import { SignalAccordion } from './SignalAccordion';

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-[1280px] px-6 py-10">
      <AboutHeroShell />

      <section className="mb-16">
        <div className="mb-6 flex flex-wrap items-baseline justify-between gap-4">
          <div>
            <p className="mb-2 font-mono text-[10px] tracking-[0.12em] text-[#a0a0a0]">METHODOLOGY</p>
            <h2 className="font-sans text-[26px] font-bold tracking-tight text-[#0a0a0a]">How the pipeline works</h2>
          </div>
          <p className="font-mono text-[11px] text-[#bbb]">Click each stage to explore</p>
        </div>
        <MethodologyTabs />
      </section>

      <section className="mb-16">
        <p className="mb-2 font-mono text-[10px] tracking-[0.12em] text-[#a0a0a0]">SIGNAL ARCHITECTURE</p>
        <h2 className="font-sans text-[26px] font-bold tracking-tight text-[#0a0a0a]">Four signal families</h2>
        <p className="mt-2 font-sans text-[14px] text-[#737373]">Click any family to expand the full methodology.</p>
        <div className="mt-6">
          <SignalAccordion />
        </div>
      </section>

      <section className="mb-16">
        <p className="mb-2 font-mono text-[10px] tracking-[0.12em] text-[#a0a0a0]">INTERACTIVE</p>
        <h2 className="font-sans text-[26px] font-bold tracking-tight text-[#0a0a0a]">Composite score simulator</h2>
        <p className="mt-2 font-sans text-[14px] text-[#737373]">
          Drag the sliders to see how signal inputs combine into a regime call.
        </p>
        <div className="mt-6 max-w-xl">
          <CompositeSimulator />
        </div>
      </section>

      <section className="border-t border-[#e5e5e5] pt-16">
        <div className="grid gap-12 lg:grid-cols-[1fr_2fr] lg:gap-16">
          <div>
            <p className="mb-2 font-mono text-[10px] tracking-[0.12em] text-[#a0a0a0]">VALIDATION</p>
            <h2 className="font-sans text-[24px] font-bold leading-tight tracking-tight text-[#0a0a0a]">
              Why public validation matters
            </h2>
            <Link
              href="/performance"
              className="mt-6 inline-flex border border-[#e5e5e5] px-4 py-2 font-mono text-[11px] text-[#555] hover:bg-[#fafafa]"
            >
              Full track record →
            </Link>
          </div>
          <div>
            <p className="font-sans text-[15px] leading-[1.8] text-[#525252]">
              Any discretionary framework can be constructed to look correct in hindsight. The discipline of publishing a
              call before the outcome is known — and logging the result without revision — is the only meaningful test.
            </p>
            <p className="mt-4 font-sans text-[15px] leading-[1.8] text-[#525252]">
              Each call is validated on next-day close-to-close spot movement. There is no partial credit and no
              ex-post edits to the record.
            </p>
          </div>
        </div>
      </section>

      <p className="mt-16 border-t border-[#f0f0f0] pt-8 font-mono text-[10px] leading-[1.8] tracking-[0.06em] text-[#c0c0c0]">
        RESEARCH AND LEARNING ONLY. NOT INVESTMENT ADVICE. ALL REGIME CALLS ARE RESEARCH OUTPUTS, NOT TRADING
        RECOMMENDATIONS.
      </p>
    </div>
  );
}
