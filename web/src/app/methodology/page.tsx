"use client";

import { Nav } from "@/components/shell/Nav";
import { Footer } from "@/components/shell/Footer";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import "katex/dist/katex.min.css";
import { useEffect, useState } from "react";

function KatexMath({ latex }: { latex: string }) {
  const [html, setHtml] = useState<string>("");

  useEffect(() => {
    try {
      const katex = require("katex");
      setHtml(
        katex.renderToString(latex, {
          throwOnError: false,
          displayMode: true,
        })
      );
    } catch {
      setHtml(latex);
    }
  }, [latex]);

  return (
    <div
      className="my-6"
      suppressHydrationWarning
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-4">
      {children}
    </p>
  );
}

export default function MethodologyPage() {
  useScrollReveal();

  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      <Nav />
      <main id="main-content" className="max-w-[1152px] mx-auto px-6 pt-28 pb-20 w-full">
        <div className="reveal mb-10 pb-6 border-b border-[var(--color-border)]">
          <SectionLabel>Methodology</SectionLabel>
          <h1 className="font-sans font-semibold text-[32px] text-[var(--color-text)] tracking-tight">
            Signal Architecture
          </h1>
          <p className="font-sans text-[15px] text-[var(--color-text-secondary)] mt-2 leading-[1.6]">
            The math behind the composite score and regime classification.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-12">
          <div>
            <div className="reveal">
              <h2 className="font-sans font-semibold text-xl text-[var(--color-text)] tracking-tight mb-4">
                Composite Score
              </h2>
              <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] mb-6">
                The regime classification is driven by a weighted composite of
                four normalized signal families. Each raw signal is first mapped
                to a percentile rank over a 252-day lookback window, then scaled
                to a [-1, +1] contribution before weighting.
              </p>

              <KatexMath latex="S = w_r \\cdot R + w_c \\cdot C + w_v \\cdot V + w_o \\cdot O" />

              <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] mb-10">
                where{" "}
                <span className="font-mono text-sm text-[var(--color-text)]">
                  w_r ≈ 0.40
                </span>
                ,{" "}
                <span className="font-mono text-sm text-[var(--color-text)]">
                  w_c ≈ 0.30
                </span>
                ,{" "}
                <span className="font-mono text-sm text-[var(--color-text)]">
                  w_v ≈ 0.20
                </span>
                , and{" "}
                <span className="font-mono text-sm text-[var(--color-text)]">
                  w_o ≈ 0.10
                </span>
                . The composite is clamped to approximately ±2.0 before regime
                mapping.
              </p>
            </div>

            <div className="reveal">
              <h2 className="font-sans font-semibold text-xl text-[var(--color-text)] tracking-tight mb-4">
                Normalization
              </h2>
              <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] mb-6">
                Raw values carry no inherent comparability across pairs or time.
                Each series is normalized to a rolling percentile rank —
                converting absolute values into a 0-100 score before entering the
                composite.
              </p>

              <KatexMath latex="P(x_t) = \\frac{\\#\\{x_i \\leq x_t \\mid i \\in [t-251, t]\\}}{252}" />

              <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] mb-10">
                Outliers beyond the 1st and 99th percentiles are winsorized to
                prevent single-day anomalies from distorting the composite.
              </p>
            </div>

            <div className="reveal">
              <h2 className="font-sans font-semibold text-xl text-[var(--color-text)] tracking-tight mb-4">
                Regime Thresholds
              </h2>
              <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] mb-6">
                The composite score is mapped to a regime label via band
                thresholds. Confidence is derived from the distance to the
                nearest band boundary and the degree of signal agreement.
              </p>

              <div className="border border-[var(--color-border)] mb-10">
                <table className="w-full border-collapse font-mono text-[11px]">
                  <thead>
                    <tr className="border-b border-[var(--color-border-subtle)] bg-[var(--color-elevated)]">
                      <th className="px-4 py-2.5 text-left text-[var(--color-text-muted)] tracking-[0.1em]">
                        REGIME
                      </th>
                      <th className="px-4 py-2.5 text-left text-[var(--color-text-muted)] tracking-[0.1em]">
                        COMPOSITE RANGE
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      ["STRONG USD STRENGTH", "S > +1.2"],
                      ["MODERATE USD STRENGTH", "+0.6 &lt; S ≤ +1.2"],
                      ["NEUTRAL", "-0.4 ≤ S ≤ +0.4"],
                      ["MODERATE USD WEAKNESS", "-1.2 ≤ S &lt; -0.6"],
                      ["STRONG USD WEAKNESS", "S &lt; -1.2"],
                      ["VOL_EXPANDING", "IV > 90th pctile (override)"],
                    ].map(([regime, range]) => (
                      <tr
                        key={regime}
                        className="border-b border-[var(--color-border-subtle)] last:border-b-0"
                      >
                        <td className="px-4 py-2.5 text-[var(--color-text)] font-medium">
                          {regime}
                        </td>
                        <td className="px-4 py-2.5 text-[var(--color-text-secondary)]">
                          {range}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="reveal">
              <h2 className="font-sans font-semibold text-xl text-[var(--color-text)] tracking-tight mb-4">
                Confidence Derivation
              </h2>
              <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] mb-6">
                Confidence is not the probability of being correct. It is an
                internal consistency metric: how far the composite sits from the
                nearest regime boundary, modulated by signal dispersion. When
                the four families agree, confidence rises. When they conflict,
                confidence compresses toward the neutral band.
              </p>

              <KatexMath latex="C = \\min(0.95, \\max(0.30, 0.50 + |S| \\cdot 0.20 - \\sigma_{signals} \\cdot 0.15))" />

              <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7]">
                where{" "}
                <span className="font-mono text-sm text-[var(--color-text)]">
                  σ_signals
                </span>{" "}
                is the standard deviation of the four normalized signal
                contributions. This penalizes mixed signals and rewards coherent
                directional alignment.
              </p>
            </div>
          </div>

          <div>
            <div className="reveal sticky top-[80px] border border-[var(--color-border)] p-6 bg-[var(--color-surface)]">
              <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-6">
                Signal Families
              </p>
              <div className="flex flex-col gap-6">
                {[
                  {
                    label: "Rate Differentials",
                    desc: "2Y sovereign yield spreads. Structural anchor of the composite.",
                    stats: [
                      ["Tenor", "2Y sovereign"],
                      ["Pairs", "G10 + INR"],
                      ["Weight", "~40%"],
                      ["Update", "Daily FRED"],
                    ],
                  },
                  {
                    label: "COT Positioning",
                    desc: "CFTC weekly non-commercial net positions as percentile ranks.",
                    stats: [
                      ["Source", "CFTC weekly"],
                      ["Lag", "3 days"],
                      ["Weight", "~30%"],
                      ["Pairs", "EUR/USD, USD/JPY, USD/INR"],
                    ],
                  },
                  {
                    label: "Realized Volatility",
                    desc: "5d and 20d realized vs 30d implied. Vol gate at 90th percentile.",
                    stats: [
                      ["Short window", "5-day realized"],
                      ["Medium window", "20-day realized"],
                      ["Forward vol", "30-day implied"],
                      ["Gate trigger", "IV > P90"],
                    ],
                  },
                  {
                    label: "OI and Risk Reversals",
                    desc: "25-delta risk reversals and open interest flows.",
                    stats: [
                      ["RR tenor", "25-delta, 1M"],
                      ["OI source", "Exchange data"],
                      ["INR special", "RBI/SEBI series"],
                      ["Weight", "~10%"],
                    ],
                  },
                ].map((fam) => (
                  <div key={fam.label}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-text-muted)] flex-shrink-0" />
                      <span className="font-sans font-semibold text-sm text-[var(--color-text)]">
                        {fam.label}
                      </span>
                    </div>
                    <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-relaxed mb-2">
                      {fam.desc}
                    </p>
                    <div className="flex flex-col gap-1">
                      {fam.stats.map(([k, v]) => (
                        <div
                          key={k}
                          className="flex justify-between font-mono text-[9px]"
                        >
                          <span className="text-[var(--color-text-muted)] tracking-wider">
                            {k.toUpperCase()}
                          </span>
                          <span className="text-[var(--color-text)] font-medium">
                            {v}
                          </span>
                        </div>
                      ))}
                    </div>
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
