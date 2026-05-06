"use client";

import Link from "next/link";
import { Nav } from "@/components/shell/Nav";
import { Footer } from "@/components/shell/Footer";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import { PAIRS } from "@/lib/constants";

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="block font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-4">
      {children}
    </span>
  );
}

export default function AboutPage() {
  useScrollReveal();

  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      <Nav />
      <main id="main-content" className="max-w-[1152px] mx-auto px-6 pt-28 pb-20 w-full">
        {/* Header */}
        <div className="reveal grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-20 mb-24 pb-16 border-b border-[var(--color-border)]">
          <div>
            <SectionLabel>About</SectionLabel>
            <h1 className="font-sans font-semibold text-[clamp(32px,4vw,48px)] text-[var(--color-text)] tracking-tight leading-[1.1] mb-8">
              A research system.
              <br />
              Public by design.
            </h1>
            <div className="flex flex-col gap-2.5">
              <Link
                href="/brief"
                className="px-5 py-2.5 bg-[var(--color-accent)] text-[var(--color-void)] font-sans text-[13px] tracking-wide transition-all duration-300 hover:bg-[var(--color-accent-hover)]"
              >
                Today&apos;s brief →
              </Link>
              <Link
                href="/terminal"
                className="px-5 py-2.5 border border-[var(--color-border)] font-sans text-[13px] text-[var(--color-text-secondary)] transition-all duration-300 hover:bg-[var(--color-elevated)] hover:text-[var(--color-text)] hover:border-[var(--color-border)]"
              >
                Open terminal →
              </Link>
              <Link
                href="/performance"
                className="px-5 py-2.5 border border-[var(--color-border)] font-sans text-[13px] text-[var(--color-text-secondary)] transition-all duration-300 hover:bg-[var(--color-elevated)] hover:text-[var(--color-text)] hover:border-[var(--color-border)]"
              >
                Track record →
              </Link>
            </div>
          </div>

          <div>
            <h2 className="font-sans font-semibold text-lg text-[var(--color-text)] tracking-tight mb-4">
              Shreyash Sakhare
            </h2>
            <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] mb-5">
              EE undergrad. Studying how G10 FX regimes form and break using
              rate differentials, COT positioning, and volatility. This is not a
              learning journal or a student project in disguise. It is a
              discretionary macro research system that happens to be public.
            </p>
            <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] mb-8">
              The site is the public trace of that work — dated calls, validated
              outcomes, no narrative added after the fact. Credibility compounds
              through calendar discipline and honest validation, not marketing.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-[var(--color-border)] border border-[var(--color-border)]">
              <div className="bg-[var(--color-surface)] p-6">
                <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-4">
                  This is
                </p>
                <ul className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-relaxed list-none p-0 m-0">
                  {[
                    "Daily regime calls for G10 pairs",
                    "Public validation trail",
                    "Composite signal from 4 families",
                    "Morning brief before market open",
                    "Terminal for dense monitoring",
                  ].map((t) => (
                    <li key={t} className="flex gap-2.5 items-start mb-2">
                      <span className="font-mono text-[11px] pt-0.5 flex-shrink-0 text-[var(--color-text-muted)]">
                        +
                      </span>
                      {t}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="bg-[var(--color-elevated)] p-6">
                <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-4">
                  This is not
                </p>
                <ul className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-relaxed list-none p-0 m-0">
                  {[
                    "A SaaS or subscription product",
                    "Investment advice",
                    "An automated trading system",
                    "Generic macro commentary",
                  ].map((t) => (
                    <li key={t} className="flex gap-2.5 items-start mb-2">
                      <span className="font-mono text-[11px] pt-0.5 flex-shrink-0 text-[var(--color-text-muted)]">
                        —
                      </span>
                      {t}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Pipeline */}
        <div className="reveal mb-24">
          <SectionLabel>Methodology</SectionLabel>
          <div className="flex items-baseline justify-between mb-8 flex-wrap gap-4">
            <h2 className="font-sans font-semibold text-[26px] text-[var(--color-text)] tracking-tight">
              How the pipeline works
            </h2>
            <p className="font-mono text-[11px] text-[var(--color-text-muted)]">
              Five stages from raw data to public call
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 border border-[var(--color-border)] mb-10">
            {[
              { n: "01", title: "Data Ingestion" },
              { n: "02", title: "Normalization" },
              { n: "03", title: "Composite" },
              { n: "04", title: "Classification" },
              { n: "05", title: "Validation" },
            ].map((s, i) => (
              <div
                key={s.n}
                className={`px-4 py-4 ${i < 4 ? "border-b md:border-b-0 md:border-r" : ""} border-[var(--color-border)] bg-[var(--color-elevated)]`}
              >
                <span className="block font-mono text-[10px] text-[var(--color-text-muted)] mb-1">
                  {s.n}
                </span>
                <span className="font-mono text-[10px] text-[var(--color-text-secondary)] font-medium tracking-wide uppercase">
                  {s.title}
                </span>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
            <div>
              <h3 className="font-sans font-semibold text-[20px] text-[var(--color-text)] tracking-tight mb-4">
                Pipeline overview
              </h3>
              <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] mb-4">
                Every trading day, a Python pipeline ingests public market data
                from multiple sources. Raw values are normalized to rolling
                percentile ranks, then combined into a weighted composite score.
                The composite is mapped to a regime label via threshold bands.
                The call is published before market open and validated the next
                trading day.
              </p>
              <p className="font-sans text-[13px] text-[var(--color-text-muted)] leading-[1.6]">
                No proprietary feeds — only publicly available data. No ex-post
                revisions. Every outcome is logged and displayed publicly.
              </p>
            </div>
            <div className="bg-[var(--color-surface)] p-6 border border-[var(--color-border)]">
              <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-4">
                Signal Weights
              </p>
              <div className="flex flex-col gap-3">
                {[
                  ["Rate Differential 2Y", "~40%"],
                  ["COT Positioning", "~30%"],
                  ["Realized Volatility", "~20%"],
                  ["OI / Risk Reversals", "~10%"],
                ].map(([label, weight]) => (
                  <div key={label} className="flex items-center gap-3">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-text-muted)] flex-shrink-0" />
                    <span className="font-mono text-[11px] text-[var(--color-text-secondary)] flex-1">
                      {label}
                    </span>
                    <span className="font-mono text-[11px] text-[var(--color-text)] font-medium">
                      {weight}
                    </span>
                  </div>
                ))}
              </div>
              <div className="mt-6 pt-4 border-t border-[var(--color-border)]">
                <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-3">
                  Thresholds
                </p>
                <div className="flex flex-col gap-2">
                  {[
                    ["STRONG USD STRENGTH", "> +1.2"],
                    ["MODERATE USD STRENGTH", "+0.6 to +1.2"],
                    ["NEUTRAL", "-0.4 to +0.4"],
                    ["MODERATE USD WEAKNESS", "-1.2 to -0.6"],
                    ["VOL_EXPANDING", "IV > 90th pctile"],
                  ].map(([label, range]) => (
                    <div
                      key={label}
                      className="flex justify-between font-mono text-[10px]"
                    >
                      <span className="text-[var(--color-text-secondary)]">
                        {label}
                      </span>
                      <span className="text-[var(--color-text)] font-medium">
                        {range}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Validation */}
        <div className="reveal border-t border-[var(--color-border)] pt-16">
          <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-16">
            <div>
              <SectionLabel>Validation</SectionLabel>
              <h2 className="font-sans font-semibold text-[26px] text-[var(--color-text)] tracking-tight leading-snug mb-4">
                Why public validation matters
              </h2>
              <Link
                href="/performance"
                className="inline-block px-5 py-2 border border-[var(--color-border)] font-mono text-[11px] text-[var(--color-text-secondary)] transition-all duration-300 hover:bg-[var(--color-elevated)] hover:text-[var(--color-text)] hover:border-[var(--color-border)]"
              >
                Full track record →
              </Link>
            </div>
            <div>
              <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] mb-5">
                Any discretionary framework can be constructed to look correct
                in hindsight. The discipline of publishing a call before the
                outcome is known — and logging the result without revision — is
                the only meaningful test.
              </p>
              <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] mb-8">
                Each call is validated on next-day close-to-close spot movement.
                If the regime was MODERATE USD WEAKNESS and EUR/USD closed
                higher, it is correct. If it closed lower, it is incorrect.
                There is no partial credit, no adjustments for vol regimes, no
                &quot;context&quot; that modifies the record.
              </p>
              <div className="grid grid-cols-3 gap-px bg-[var(--color-border)] border border-[var(--color-border)]">
                {[
                  { label: "7D ACCURACY", value: "—", sub: "Live on Performance" },
                  { label: "CALLS LOGGED", value: "—", sub: "Live on Performance" },
                  { label: "PAIRS COVERED", value: String(PAIRS.length), sub: PAIRS.map(p => p.display).join(", ") },
                ].map((m) => (
                  <div key={m.label} className="bg-[var(--color-surface)] p-5">
                    <p className="font-mono text-[9px] tracking-[0.12em] text-[var(--color-text-muted)] uppercase mb-2">
                      {m.label}
                    </p>
                    <p className="font-mono text-[26px] font-medium text-[var(--color-text)] tracking-tight tabular-nums">
                      {m.value}
                    </p>
                    <p className="font-mono text-[9px] text-[var(--color-text-muted)] mt-1">
                      {m.sub}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
