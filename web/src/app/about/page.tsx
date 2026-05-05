import Link from "next/link";
import { Nav } from "@/components/shell/Nav";
import { Footer } from "@/components/shell/Footer";
import { PAIRS } from "@/lib/constants";

export default function AboutPage() {
  return (
    <div className="min-h-screen flex flex-col bg-white">
      <Nav />
      <main className="flex-1 max-w-[1152px] mx-auto px-6 py-14 pb-20 w-full">
        {/* Section 1: Header */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-20 mb-20 pb-16 border-b border-shell-border">
          <div>
            <p className="font-mono text-[10px] text-shell-muted tracking-[0.12em] mb-5">
              ABOUT
            </p>
            <h1 className="font-sans font-extrabold text-[40px] text-shell-text tracking-tight leading-[1.05] mb-7">
              A research system.
              <br />
              Public by design.
            </h1>
            <div className="flex gap-2 mb-7">
              {PAIRS.map((p) => (
                <span
                  key={p.label}
                  className="inline-block w-6 h-[3px]"
                  style={{ background: p.pairColor }}
                />
              ))}
            </div>
            <div className="flex flex-col gap-2">
              <Link
                href="/brief"
                className="font-sans text-[13px] font-semibold text-white bg-shell-text px-4 py-2.5 text-left"
              >
                Today&apos;s brief →
              </Link>
              <Link
                href="/terminal"
                className="font-sans text-[13px] font-medium text-shell-text border border-shell-border px-4 py-2.5 text-left"
              >
                Open terminal →
              </Link>
              <Link
                href="/performance"
                className="font-sans text-[13px] font-medium text-shell-text border border-shell-border px-4 py-2.5 text-left"
              >
                Track record →
              </Link>
            </div>
          </div>
          <div>
            <h2 className="font-sans font-bold text-lg text-shell-text tracking-tight mb-4">
              Shreyash Sakhare
            </h2>
            <p className="font-sans text-[15px] text-shell-secondary leading-relaxed mb-5">
              EE undergrad. Studying how G10 FX regimes form and break using
              rate differentials, COT positioning, and volatility. This is not a
              learning journal or a student project in disguise. It is a
              discretionary macro research system that happens to be public.
            </p>
            <p className="font-sans text-[15px] text-shell-secondary leading-relaxed mb-7">
              The site is the public trace of that work — dated calls, validated
              outcomes, no narrative added after the fact. Credibility compounds
              through calendar discipline and honest validation, not marketing.
            </p>

            {/* This is / This is not */}
            <div
              className="grid grid-cols-1 md:grid-cols-2 gap-px"
              style={{ background: "#e5e5e5" }}
            >
              {[
                {
                  title: "THIS IS",
                  color: "#16a34a",
                  sign: "+",
                  items: [
                    "Daily regime calls for G10 pairs",
                    "Public validation trail",
                    "Composite signal from 4 families",
                    "Morning brief before market open",
                    "Terminal for dense monitoring",
                  ],
                },
                {
                  title: "THIS IS NOT",
                  color: "#dc2626",
                  sign: "-",
                  items: [
                    "A SaaS or subscription product",
                    "Investment advice",
                    "An automated trading system",
                    "Generic macro commentary",
                  ],
                },
              ].map((col) => (
                <div key={col.title} className="bg-white p-5">
                  <p
                    className="font-mono text-[10px] tracking-[0.1em] mb-3"
                    style={{ color: col.color }}
                  >
                    {col.title}
                  </p>
                  <ul className="font-sans text-[13px] text-shell-secondary leading-relaxed list-none p-0 m-0">
                    {col.items.map((t) => (
                      <li
                        key={t}
                        className="flex gap-2.5 items-start mb-1.5"
                      >
                        <span
                          className="font-mono text-[11px] pt-0.5 flex-shrink-0"
                          style={{ color: col.color }}
                        >
                          {col.sign}
                        </span>
                        {t}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Section 2: Pipeline Walkthrough */}
        <div className="mb-18">
          <div className="flex items-baseline justify-between mb-7">
            <div>
              <p className="font-mono text-[10px] text-shell-muted tracking-[0.12em] mb-2.5">
                METHODOLOGY
              </p>
              <h2 className="font-sans font-bold text-[26px] text-shell-text tracking-tight">
                How the pipeline works
              </h2>
            </div>
            <p className="font-mono text-[11px] text-[#bbb]">
              Five stages from raw data to public call
            </p>
          </div>
          <div className="border border-shell-border">
            <div className="grid grid-cols-1 md:grid-cols-5 border-b border-shell-border bg-[#fafafa]">
              {[
                { n: "01", title: "Data Ingestion", color: "#4BA3E3" },
                { n: "02", title: "Normalization", color: "#F5923A" },
                { n: "03", title: "Composite", color: "#D94030" },
                { n: "04", title: "Classification", color: "#888" },
                { n: "05", title: "Validation", color: "#22c55e" },
              ].map((s) => (
                <div
                  key={s.n}
                  className="px-3 py-3.5 border-r border-[#f0f0f0] last:border-r-0"
                >
                  <span
                    className="block font-mono text-[10px] font-bold mb-1"
                    style={{ color: s.color }}
                  >
                    {s.n}
                  </span>
                  <span className="font-mono text-[10px] text-shell-text font-semibold tracking-wide">
                    {s.title.toUpperCase()}
                  </span>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2">
              <div className="p-8 border-r border-[#f0f0f0]">
                <h3 className="font-sans font-bold text-[22px] text-shell-text tracking-tight mb-3.5">
                  Pipeline overview
                </h3>
                <p className="font-sans text-sm text-shell-secondary leading-relaxed mb-4">
                  Every trading day, a Python pipeline ingests public market
                  data from multiple sources. Raw values are normalized to
                  rolling percentile ranks, then combined into a weighted
                  composite score. The composite is mapped to a regime label via
                  threshold bands. The call is published before market open and
                  validated the next trading day.
                </p>
                <p className="font-sans text-[13px] text-[#888] leading-relaxed">
                  No proprietary feeds — only publicly available data. No
                  ex-post revisions. Every outcome is logged and displayed
                  publicly.
                </p>
              </div>
              <div className="p-8 bg-[#fafafa]">
                <p className="font-mono text-[10px] text-[#bbb] tracking-[0.12em] mb-2">
                  SIGNAL WEIGHTS
                </p>
                <div className="flex flex-col gap-2">
                  {[
                    ["Rate Differential 2Y", "~40%", "#4BA3E3"],
                    ["COT Positioning", "~30%", "#F5923A"],
                    ["Realized Volatility", "~20%", "#D94030"],
                    ["OI / Risk Reversals", "~10%", "#888"],
                  ].map(([label, weight, color]) => (
                    <div key={label} className="flex items-center gap-3">
                      <span
                        className="w-2 h-2 flex-shrink-0"
                        style={{ background: color }}
                      />
                      <span className="font-mono text-[11px] text-[#555] flex-1">
                        {label}
                      </span>
                      <span className="font-mono text-[11px] text-shell-text font-bold">
                        {weight}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="mt-6 pt-4 border-t border-[#e5e5e5]">
                  <p className="font-mono text-[10px] text-[#bbb] tracking-[0.12em] mb-2">
                    THRESHOLDS
                  </p>
                  <div className="flex flex-col gap-1.5">
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
                        <span className="text-[#555]">{label}</span>
                        <span className="text-shell-text font-bold">
                          {range}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Section 3: Validation Philosophy */}
        <div className="border-t border-shell-border pt-16">
          <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-16">
            <div>
              <p className="font-mono text-[10px] text-shell-muted tracking-[0.12em] mb-3.5">
                VALIDATION
              </p>
              <h2 className="font-sans font-bold text-2xl text-shell-text tracking-tight leading-snug mb-4">
                Why public validation matters
              </h2>
              <Link
                href="/performance"
                className="inline-block font-mono text-[11px] text-[#555] border border-shell-border px-4 py-2 mt-4"
              >
                Full track record →
              </Link>
            </div>
            <div>
              <p className="font-sans text-[15px] text-shell-secondary leading-relaxed mb-5">
                Any discretionary framework can be constructed to look correct in
                hindsight. The discipline of publishing a call before the outcome
                is known — and logging the result without revision — is the only
                meaningful test.
              </p>
              <p className="font-sans text-[15px] text-shell-secondary leading-relaxed mb-7">
                Each call is validated on next-day close-to-close spot movement.
                If the regime was MODERATE USD WEAKNESS and EUR/USD closed
                higher, it is correct. If it closed lower, it is incorrect.
                There is no partial credit, no adjustments for vol regimes, no
                &quot;context&quot; that modifies the record.
              </p>
              <div
                className="grid grid-cols-3 gap-px"
                style={{ background: "#e5e5e5" }}
              >
                {[
                  {
                    label: "7D ACCURACY",
                    value: "77.8%",
                    color: "#16a34a",
                  },
                  { label: "CALLS LOGGED", value: "27", color: "#0a0a0a" },
                  {
                    label: "PAIRS COVERED",
                    value: `${PAIRS.length}`,
                    color: "#4BA3E3",
                  },
                ].map((m) => (
                  <div key={m.label} className="bg-white p-4">
                    <p className="font-mono text-[9px] text-[#aaa] tracking-[0.1em] mb-2">
                      {m.label}
                    </p>
                    <p
                      className="font-mono text-[26px] font-bold tracking-tight"
                      style={{ color: m.color }}
                    >
                      {m.value}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="mt-10 pt-6 border-t border-[#f0f0f0]">
            <p className="font-mono text-[10px] text-[#c0c0c0] tracking-wider leading-relaxed">
              RESEARCH AND LEARNING ONLY. NOT INVESTMENT ADVICE. ALL REGIME
              CALLS ARE RESEARCH OUTPUTS, NOT TRADING RECOMMENDATIONS.
            </p>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
