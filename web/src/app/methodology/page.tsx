"use client";

import { Footer } from "@/components/shell/Footer";
import { Nav } from "@/components/shell/Nav";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import { PAIRS } from "@/lib/constants";
import "katex/dist/katex.min.css";
import { useEffect, useState } from "react";

/* ── KaTeX wrapper with forced bright text for dark terminal ───────────── */

function KatexMath({ latex }: { latex: string }) {
  const [html, setHtml] = useState<string>("");

  useEffect(() => {
    try {
      const katex = require("katex");
      setHtml(
        katex.renderToString(latex, {
          throwOnError: false,
          displayMode: true,
        }),
      );
    } catch {
      setHtml(latex);
    }
  }, [latex]);

  return (
    <div
      className="my-6 katex-wrapper"
      suppressHydrationWarning
      // biome-ignore lint/security/noDangerouslySetInnerHtml: KaTeX HTML is server-rendered and sanitized
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

function Subsection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="reveal mb-10">
      <h2 className="font-sans font-semibold text-xl text-[var(--color-text)] tracking-tight mb-4">
        {title}
      </h2>
      {children}
    </div>
  );
}

function Body({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] mb-6">
      {children}
    </p>
  );
}

function Mono({ children }: { children: React.ReactNode }) {
  return (
    <span className="font-mono text-sm text-[var(--color-text)]">
      {children}
    </span>
  );
}

/* ── pair colour helper ────────────────────────────────────────────────── */

function PairDot({ color }: { color: string }) {
  return (
    <span
      className="inline-block w-2 h-2 mr-2"
      style={{ backgroundColor: color }}
    />
  );
}

/* ── page ──────────────────────────────────────────────────────────────── */

export default function MethodologyPage() {
  useScrollReveal();

  const pairMap = Object.fromEntries(PAIRS.map((p) => [p.label, p.pairColor]));

  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      <Nav />
      <main
        id="main-content"
        className="max-w-[1152px] mx-auto px-6 pt-28 pb-20 w-full"
      >
        {/* KaTeX bright-colour override lives in globals.css */}

        {/* Header */}
        <div className="reveal mb-10 pb-6 border-b border-[var(--color-border)]">
          <SectionLabel>Methodology</SectionLabel>
          <h1 className="font-sans font-semibold text-[32px] text-[var(--color-text)] tracking-tight">
            Signal Architecture
          </h1>
          <Body>
            The regime classification is driven by a deterministic three-layer
            framework. Every number is computed from causal windows — today's
            observation is scored only against history that was available at
            close of business <Mono>t − 1</Mono>. No lookahead.
          </Body>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-12">
          <div>
            {/* ── Layer 1 ─────────────────────────────────────────────── */}
            <Subsection title="Layer 1 — Regime Gate">
              <Body>
                The gate determines the macro environment from rate
                differentials, carry momentum, breakeven-inflation shocks, and
                spot stress. It is the first filter; if the gate is invalidated
                (stale or missing data), the system falls back to neutral.
              </Body>

              <Body>
                <strong className="text-[var(--color-text)]">
                  Rate differential z-score.
                </strong>{" "}
                The 2-year sovereign yield spread (US vs counterparty) is
                converted to a rolling z-score over a 252-day causal window with
                a 90-day minimum:
              </Body>
              <KatexMath latex="z_{\text{rate}} = \frac{x_t - \mu_{[t-251,\,t-1]}}{\sigma_{[t-251,\,t-1]}}" />

              <Body>
                <strong className="text-[var(--color-text)]">
                  Momentum check.
                </strong>{" "}
                Carry momentum{" "}
                <Mono>
                  m = x_t − x{"{"}t−20{"}"}
                </Mono>{" "}
                flags fading trends. When <Mono>z ≥ 1.15</Mono> and{" "}
                <Mono>m ≤ −0.25</Mono> simultaneously, the regime flips to{" "}
                <Mono>CARRY_COLLAPSE</Mono>.
              </Body>

              <Body>
                <strong className="text-[var(--color-text)]">
                  Policy-breakout override.
                </strong>{" "}
                If breakeven inflation moves <Mono>≥ 12 bps</Mono> in 5 days
                while <Mono>|z| ≥ 2.0</Mono>, the gate overrides to{" "}
                <Mono>USD_POLICY_BREAKOUT</Mono>.
              </Body>

              <Body>
                <strong className="text-[var(--color-text)]">
                  Liquidity-shock override.
                </strong>{" "}
                If 21-day spot-return z-score <Mono>|d| ≥ 2.5</Mono>, the gate
                triggers <Mono>LIQUIDITY_SHOCK</Mono> regardless of composite.
              </Body>

              <Body>
                <strong className="text-[var(--color-text)]">
                  Composite hysteresis.
                </strong>{" "}
                When no override fires, the composite score maps to a five-tier
                Schmitt trigger with memory of yesterday's tier:
              </Body>
              <KatexMath latex="\\text{snap}(c) = \\begin{cases} 4 & c > 1.0 \\ 3 & c > 0.4 \\ 2 & -0.4 \\leq c \\leq 0.4 \\ 1 & c < -0.4 \\ 0 & c < -1.0 \\end{cases}" />
              <Body>
                Tier changes of only one step are deferred unless the composite
                crosses a tighter bound (e.g. tier 4 requires{" "}
                <Mono>c ≥ 0.85</Mono> to hold, not just <Mono>{"> 0.4"}</Mono>).
              </Body>
            </Subsection>

            {/* ── Layer 2 ─────────────────────────────────────────────── */}
            <Subsection title="Layer 2 — Directional Bias & Conviction">
              <Body>
                Layer 2 translates the gate's macro read into a discrete
                directional bias (LONG / SHORT / NEUTRAL) and an integer
                conviction score <Mono>1–5</Mono>.
              </Body>

              <Body>
                <strong className="text-[var(--color-text)]">
                  Positioning percentile.
                </strong>{" "}
                CFTC non-commercial net positions are ranked over a 156-week
                lookback. The percentile <Mono>π</Mono> feeds three metrics:
              </Body>
              <KatexMath latex="\\phi_{\\text{upper}}(\\pi) = \\max(0, \\min(1, \\frac{\\pi - 90}{10})) \quad \\phi_{\\text{lower}}(\\pi) = \\max(0, \\min(1, \\frac{10 - \\pi}{10}))" />
              <Body>
                Crowding flag: <Mono>π ≥ 90</Mono> or <Mono>π ≤ 10</Mono>.
                Crowding veto: <Mono>π ≥ 97</Mono> or <Mono>π ≤ 3</Mono>.
              </Body>

              <Body>
                <strong className="text-[var(--color-text)]">
                  Marcus B clash veto.
                </strong>{" "}
                If the rate z-score and positioning percentile point in opposite
                directions (both materially non-zero), the bias is forced to
                NEUTRAL and conviction is capped at 3.
              </Body>

              <Body>
                <strong className="text-[var(--color-text)]">
                  Conviction multiplier.
                </strong>{" "}
                Alignment bonus when rate and positioning agree; penalty when
                they conflict or when crowding is elevated:
              </Body>
              <KatexMath latex="m_{\\pi} = \\max(0.52, \\min(1.08, \\; (1 - 0.48 \\cdot p_{\\text{crowd}}) \\cdot a_{\\text{align}} \\;))" />
              <Body>
                where <Mono>a = 1.0</Mono> if rate and positioning agree,{" "}
                <Mono>0.72</Mono> if they conflict.
              </Body>

              <Body>
                <strong className="text-[var(--color-text)]">
                  Conviction score.
                </strong>{" "}
                Base conviction is anchored to the composite magnitude, then
                scaled by <Mono>m_π</Mono>:
              </Body>
              <KatexMath latex="C = \\text{round}(\\max(1, \\min(5, \\; (3 + \\text{clip}(S, -2, 2)) \\cdot m_{\\pi} \\;)))" />
              <Body>
                If the gate is invalidated, crowding is veto-level, or Marcus B
                clashes, conviction is hard-capped at 3.
              </Body>
            </Subsection>

            {/* ── Layer 3 ─────────────────────────────────────────────── */}
            <Subsection title="Layer 3 — Execution & Timing">
              <Body>
                Layer 3 produces entry timing (ENTER / WAIT), position sizing
                (FULL / HALF), and stop levels from realized volatility, risk
                reversal skew, and intraday microstructure.
              </Body>

              <Body>
                <strong className="text-[var(--color-text)]">
                  Realized-vol rank.
                </strong>{" "}
                The 21-day annualized realized vol is scored against its
                empirical CDF over a trailing 3-year (756 session) causal
                window. Let <Mono>q^σ_t</Mono> denote the quantile. Entry is
                blocked when <Mono>q^σ_t {"> 0.88"}</Mono>. Full size requires{" "}
                <Mono>q^σ_t ≤ 0.70</Mono>.
              </Body>

              <Body>
                <strong className="text-[var(--color-text)]">
                  Risk-reversal skew.
                </strong>{" "}
                25-delta risk reversal (implied-vol difference call−put) is
                z-scored causally using only <Mono>[t−252, t−1]</Mono> for mean
                and standard deviation. The alignment score{" "}
                <Mono>A_t = sign(bias) · sign(z_t)</Mono>. A skew-reversal flag{" "}
                <Mono>R_t</Mono> fires on a sign change across consecutive
                sessions where both legs are material{" "}
                <Mono>(|z| {"> 0.35"})</Mono>.
              </Body>

              <Body>
                <strong className="text-[var(--color-text)]">
                  Marcus enter rule.
                </strong>{" "}
                Entry requires: bias ≠ NEUTRAL, conviction ≥ 3,{" "}
                <Mono>q^σ_t ≤ 0.88</Mono>, no skew reversal, and no strong
                directional skew contradiction unless conviction is high enough
                to absorb it.
              </Body>

              <Body>
                <strong className="text-[var(--color-text)]">
                  Lena + Chen sizing.
                </strong>{" "}
                Full size only when: timing = ENTER, conviction ≥ 4,{" "}
                <Mono>q^σ_t ≤ 0.70</Mono>, skew alignment ≥ 0, and crowding
                penalty <Mono>p_crowd ≤ 0.35</Mono>. Otherwise HALF.
              </Body>

              <Body>
                <strong className="text-[var(--color-text)]">
                  Stop level.
                </strong>{" "}
                Stop buffer is <Mono>max(1.5 · ADR_20, MIE_proxy)</Mono> where
                ADR is the mean daily range and MIE proxy is the worst adverse
                intraday move from the open against the directional bias over 20
                days:
              </Body>
              <KatexMath latex="\\text{Stop} = \\begin{cases} S_t - \\text{buffer} & \\text{LONG} \\ S_t + \\text{buffer} & \\text{SHORT} \\ \\text{none} & \\text{NEUTRAL} \\end{cases}" />
            </Subsection>

            {/* ── Per-Pair Differences ────────────────────────────────── */}
            <Subsection title="Per-Pair Methodology">
              <Body>
                The three pairs share the same three-layer architecture but
                differ in weighting, data sources, and special-signal handling.
              </Body>

              {/* EURUSD */}
              <div className="mb-8">
                <h3 className="font-sans font-semibold text-lg text-[var(--color-text)] tracking-tight mb-3 flex items-center">
                  <PairDot color={pairMap.EURUSD} />
                  EUR / USD
                </h3>
                <Body>
                  Primary driver is the US–Germany 2-year and 10-year yield
                  spread (FRED <Mono>DGS2</Mono> vs ECB data-api). Composite
                  weights: rate spread <Mono>30%</Mono>, COT leverage{" "}
                  <Mono>20%</Mono>, asset-manager positioning <Mono>10%</Mono>,
                  vol signal <Mono>10%</Mono>, correlation signal{" "}
                  <Mono>15%</Mono>, oil signal <Mono>8%</Mono>, DXY{" "}
                  <Mono>7%</Mono>. Risk-reversal modifier is active: when EURUSD
                  25Δ RR z-score confirms the composite (|z| {"> 0.5"}), the
                  composite is multiplied by <Mono>1.15</Mono>; when it
                  contradicts (|z| {"> 1.5"}), it is multiplied by{" "}
                  <Mono>0.60</Mono> and flagged <Mono>OPTIONS_DIVERGENCE</Mono>.
                </Body>
              </div>

              {/* USDJPY */}
              <div className="mb-8">
                <h3 className="font-sans font-semibold text-lg text-[var(--color-text)] tracking-tight mb-3 flex items-center">
                  <PairDot color={pairMap.USDJPY} />
                  USD / JPY
                </h3>
                <Body>
                  Primary driver is the US–Japan yield spread (FRED{" "}
                  <Mono>DGS2</Mono> vs MOF JGBs). Composite weights: rate spread{" "}
                  <Mono>25%</Mono>, COT leverage <Mono>20%</Mono>, asset-manager{" "}
                  <Mono>10%</Mono>, vol <Mono>10%</Mono>, correlation{" "}
                  <Mono>15%</Mono>, oil <Mono>10%</Mono>, gold <Mono>5%</Mono>,
                  DXY <Mono>5%</Mono>. Carry-trade dynamics are explicitly
                  monitored: when carry risk-adjusted z-score is elevated (≥
                  1.15) but 20-day momentum is fading (≤ −0.25), the gate
                  triggers <Mono>CARRY_COLLAPSE</Mono>. Confidence receives a +5
                  pp bonus when the special carry signal <Mono>{"> 0.5"}</Mono>.
                </Body>
              </div>

              {/* USDINR */}
              <div className="mb-8">
                <h3 className="font-sans font-semibold text-lg text-[var(--color-text)] tracking-tight mb-3 flex items-center">
                  <PairDot color={pairMap.USDINR} />
                  USD / INR
                </h3>
                <Body>
                  INR does not use COT positioning (no liquid CFTC proxy).
                  Instead, the composite is built from: oil-INR correlation{" "}
                  <Mono>25%</Mono>, DXY-INR correlation <Mono>20%</Mono>, FPI
                  20-day flow <Mono>25%</Mono>, RBI intervention score{" "}
                  <Mono>20%</Mono>, and US–India 10-year spread <Mono>10%</Mono>
                  . RBI flags map directly: ACTIVE SUPPORT <Mono>−0.30</Mono>,
                  ACTIVE CAPPING <Mono>+0.20</Mono>, otherwise <Mono>0.0</Mono>.
                  When Brent is above its 80th percentile, confidence receives a
                  −5 pp adjustment reflecting external-account vulnerability.
                </Body>
              </div>
            </Subsection>

            {/* ── Confidence ──────────────────────────────────────────── */}
            <Subsection title="Confidence Derivation">
              <Body>
                Confidence is not a probability of being correct. It is an
                internal consistency metric: distance from the nearest regime
                boundary, modulated by signal agreement, pair-specific
                adjustments, and an institutional −5 pp haircut.
              </Body>

              <Body>
                First, the distance to the nearest of the four thresholds{" "}
                <Mono>(−1.0, −0.4, 0.4, 1.0)</Mono> is computed:
              </Body>
              <KatexMath latex="d = \\min_{\\tau} |S - \\tau| \quad \\text{for} \\; \\tau \\in \\{-1.0, -0.4, 0.4, 1.0\\}" />
              <KatexMath latex="\\text{base} = \\text{clip}\\left(\\frac{d}{0.6}, \\; 0.10, \\; 0.90\\right)" />

              <Body>
                Agreement bonus (+5 pp each): rate and positioning have the same
                sign; both have magnitude {"> 0.3"}.
              </Body>

              <Body>
                Pair adjustments: USDJPY carry signal {"> 0.5"} adds +5 pp;
                USDINR Brent above P80 subtracts −5 pp.
              </Body>

              <Body>
                Raw confidence is clipped to [0.40, 0.95], then the
                institutional haircut is applied:
              </Body>
              <KatexMath latex="C = \\text{clip}\\left( \\text{clip}(\\text{base} + \\text{bonus} + \\text{pair}, \\; 0.40, \\; 0.95) - 0.05, \\; 0.40, \\; 0.90 \\right)" />
            </Subsection>

            {/* ── Validation Methodology ──────────────────────────────── */}
            <Subsection title="Validation Methodology">
              <Body>
                Every regime call is validated out-of-sample at two horizons:
                T+5 (one trading week) and T+20 (one trading month). Validation
                is append-only; once written, a validation row is never mutated.
              </Body>

              <Body>
                <strong className="text-[var(--color-text)]">
                  Directional outcome.
                </strong>{" "}
                The log-return in basis points between call-date spot and
                horizon-date spot is:
              </Body>
              <KatexMath latex="r_{h} = 10{,}000 \\cdot \\ln\\left(\\frac{S_{t+h}}{S_t}\\right)" />
              <Body>
                A 5 bps dead-band filters noise: UP if <Mono>r {"> 5"}</Mono>,
                DOWN if <Mono>r {"< -5"}</Mono>, otherwise NEUTRAL.
              </Body>

              <Body>
                <strong className="text-[var(--color-text)]">
                  Correctness.
                </strong>{" "}
                A BULLISH call is correct only if realized is UP; BEARISH only
                if DOWN; NEUTRAL only if realized is NEUTRAL.
              </Body>

              <Body>
                <strong className="text-[var(--color-text)]">
                  Brier score.
                </strong>{" "}
                For each directional call (non-neutral), the Brier score is{" "}
                <Mono>(p − y)²</Mono> where <Mono>p</Mono> is the confidence and{" "}
                <Mono>y = 1</Mono> if correct, <Mono>0</Mono> otherwise. The
                random-guess baseline for three outcomes is <Mono>0.333</Mono>.
                Brier skill is reported as{" "}
                <Mono>(baseline − mean) / baseline</Mono>.
              </Body>

              <Body>
                <strong className="text-[var(--color-text)]">Win rate.</strong>{" "}
                Computed only over directional calls (excludes neutral) to avoid
                inflating accuracy with no-trade states.
              </Body>
            </Subsection>

            {/* ── Data Sources ────────────────────────────────────────── */}
            <Subsection title="Data Sources & Fallback Chain">
              <Body>
                All data is fetched daily via an async ingestion engine with
                explicit backoff and retry. Missing primary sources trigger a
                documented fallback chain; if all fail, the signal is marked
                stale rather than interpolated.
              </Body>

              <div className="border border-[var(--color-border)] mb-6">
                <table className="w-full border-collapse font-mono text-[11px]">
                  <thead>
                    <tr className="border-b border-[var(--color-border-subtle)] bg-[var(--color-elevated)]">
                      <th className="px-4 py-2.5 text-left text-[var(--color-text-muted)] tracking-[0.1em]">
                        SIGNAL
                      </th>
                      <th className="px-4 py-2.5 text-left text-[var(--color-text-muted)] tracking-[0.1em]">
                        PRIMARY
                      </th>
                      <th className="px-4 py-2.5 text-left text-[var(--color-text-muted)] tracking-[0.1em]">
                        FALLBACK
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      ["US Yields", "FRED (DGS2, DGS10)", "—"],
                      ["DE Yields", "ECB data-api", "—"],
                      ["JP Yields", "MOF Japan CSV", "—"],
                      ["FX Spot", "Alpha Vantage", "yfinance"],
                      ["COT Positioning", "CFTC weekly", "—"],
                      ["Implied Vol", "Yahoo Finance (^EVZ, ^JYVIX)", "—"],
                      ["CME OI", "CME volume/OI CSV", "—"],
                      ["Risk Reversal", "yfinance (FXE options)", "—"],
                      ["Macro Calendar", "Investing.com", "—"],
                    ].map(([sig, pri, fb]) => (
                      <tr
                        key={sig}
                        className="border-b border-[var(--color-border-subtle)] last:border-b-0"
                      >
                        <td className="px-4 py-2.5 text-[var(--color-text)] font-medium">
                          {sig}
                        </td>
                        <td className="px-4 py-2.5 text-[var(--color-text-secondary)]">
                          {pri}
                        </td>
                        <td className="px-4 py-2.5 text-[var(--color-text-secondary)]">
                          {fb}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Subsection>
          </div>

          {/* ── Sidebar ─────────────────────────────────────────────── */}
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
                      ["Tenor", "2Y + 10Y"],
                      ["Window", "252d z-score"],
                      ["Min periods", "90"],
                      ["Weight", "25–30%"],
                    ],
                  },
                  {
                    label: "COT Positioning",
                    desc: "CFTC weekly non-commercial net positions as 156-week percentile ranks.",
                    stats: [
                      ["Source", "CFTC Disaggregated"],
                      ["Lag", "3 days"],
                      ["Weight", "20%"],
                      ["Pairs", "EUR, JPY only"],
                    ],
                  },
                  {
                    label: "Realized Volatility",
                    desc: "21d annualized realized vs 3-yr empirical CDF. Vol gate at 88th percentile.",
                    stats: [
                      ["Short window", "21-day realized"],
                      ["Rank window", "756 sessions"],
                      ["Enter max", "q ≤ 0.88"],
                      ["Full-size max", "q ≤ 0.70"],
                    ],
                  },
                  {
                    label: "Risk Reversal Skew",
                    desc: "25-delta risk reversal in implied-vol points. Causal z against 252d history.",
                    stats: [
                      ["RR tenor", "25-delta, 1M"],
                      ["Z window", "252d causal"],
                      ["Reversal thresh", "|z| > 0.35"],
                      ["Pairs", "EURUSD active"],
                    ],
                  },
                  {
                    label: "Open Interest",
                    desc: "CME futures OI delta and price-alignment flag.",
                    stats: [
                      ["OI source", "CME daily CSV"],
                      ["Products", "6E, 6J"],
                      ["Unwind flag", "Crowded COT + 3d shrinking OI"],
                      ["Weight", "Implicit in flags"],
                    ],
                  },
                ].map((fam) => (
                  <div key={fam.label}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="w-1.5 h-1.5 bg-[var(--color-text-muted)] flex-shrink-0" />
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

              <div className="mt-8 pt-6 border-t border-[var(--color-border)]">
                <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-4">
                  Regime Thresholds
                </p>
                <div className="flex flex-col gap-2 font-mono text-[10px]">
                  {[
                    ["RISK_OFF_DOLLAR_BID", "S > +1.0"],
                    ["GROWTH_SURPRISE_USD", "+0.4 < S ≤ +1.0"],
                    ["NEUTRAL", "−0.4 ≤ S ≤ +0.4"],
                    ["RISK_ON_DOLLAR_OFF", "−1.0 ≤ S < −0.4"],
                    ["LIQUIDITY_SHOCK", "Spot stress |z| ≥ 2.5"],
                    ["USD_POLICY_BREAKOUT", "BEI shock + |z| ≥ 2.0"],
                    ["CARRY_COLLAPSE", "z ≥ 1.15, m ≤ −0.25"],
                  ].map(([regime, range]) => (
                    <div
                      key={regime}
                      className="flex justify-between border-b border-[var(--color-border-subtle)] last:border-b-0 pb-1.5 last:pb-0"
                    >
                      <span className="text-[var(--color-text)] font-medium">
                        {regime}
                      </span>
                      <span className="text-[var(--color-text-secondary)]">
                        {range}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
