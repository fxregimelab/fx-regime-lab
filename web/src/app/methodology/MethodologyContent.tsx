"use client";

import MethodologyFlowchart from "@/components/methodology/MethodologyFlowchart";
import SignalDecomposition from "@/components/methodology/SignalDecomposition";
import { useScrollReveal } from "@/hooks/useScrollReveal";
import { PAIRS } from "@/lib/constants";
import "katex/dist/katex.min.css";
import { useEffect, useState } from "react";

/* ── KaTeX wrapper with forced bright text for dark terminal ───────────── */

function KatexMath({ latex }: { latex: string }) {
  const [html, setHtml] = useState<string>("");

  useEffect(() => {
    import("katex")
      .then((mod) => {
        setHtml(
          mod.default.renderToString(latex, {
            throwOnError: false,
            displayMode: true,
          }),
        );
      })
      .catch(() => {
        setHtml(latex);
      });
  }, [latex]);

  return (
    <div
      className="my-6 katex-wrapper"
      suppressHydrationWarning
      // biome-ignore lint/security/noDangerouslySetInnerHtml: KaTeX HTML is trusted
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

/* ── Piecewise function rendered as semantic HTML ──────────────────────── */

function Piecewise({
  lhs,
  cases,
}: {
  lhs: React.ReactNode;
  cases: [React.ReactNode, React.ReactNode][];
}) {
  return (
    <div className="my-6 flex items-start gap-3 font-mono text-[14px] text-[var(--color-text)] leading-relaxed">
      <div className="shrink-0 pt-0.5">{lhs}</div>
      <div className="text-[var(--color-text)] text-xl leading-none pt-0.5">
        {"{"}
      </div>
      <div className="flex flex-col gap-0.5">
        {cases.map(([value, condition]) => (
          <div key={String(condition)} className="flex gap-4">
            <span className="min-w-[2ch] text-right tabular-nums">{value}</span>
            <span className="text-[var(--color-text-muted)]">{condition}</span>
          </div>
        ))}
      </div>
    </div>
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
  id,
  children,
}: {
  title: string;
  id?: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="mb-16 scroll-mt-28">
      <h2 className="font-sans font-semibold text-xl text-[var(--color-text)] tracking-tight mb-4">
        {title}
      </h2>
      {children}
    </section>
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

/* ── page content ──────────────────────────────────────────────────────── */

export default function MethodologyContent() {
  useScrollReveal();

  const pairMap = Object.fromEntries(PAIRS.map((p) => [p.label, p.pairColor]));

  return (
    <>
      {/* KaTeX bright-colour override lives in globals.css */}

      {/* Header */}
      <section
        id="overview"
        className="mb-10 pb-6 border-b border-[var(--color-border)] scroll-mt-28"
      >
        <SectionLabel>Methodology</SectionLabel>
        <h1 className="font-sans font-semibold text-[32px] text-[var(--color-text)] tracking-tight">
          Signal Architecture
        </h1>
        <Body>
          The regime classification is driven by a deterministic three-layer
          framework. Every number is computed from causal windows — today's
          observation is scored only against history that was available at close
          of business <Mono>t − 1</Mono>. No lookahead.
        </Body>
      </section>

      {/* ── Pipeline Flowchart ──────────────────────────────────────── */}
      <section id="architecture" className="scroll-mt-28">
        <MethodologyFlowchart />
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-12">
        <div>
          {/* ── Layer 1 ─────────────────────────────────────────────── */}
          <Subsection title="Layer 1 — Regime Gate" id="layer1">
            <Body>
              The gate determines the macro environment from rate differentials,
              carry momentum, breakeven-inflation shocks, and spot stress. First
              filter; if invalidated (stale or missing data), the system falls
              back to neutral.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">
                Rate differential z-score.
              </strong>{" "}
              The carry-risk-adjusted spread is converted to a rolling MAD
              Z-score over a 252-day causal window with a 90-day minimum. The
              observation at <Mono>t</Mono> is scored against median and MAD
              computed from <Mono>[t−251, t−1]</Mono> only — no lookahead:
            </Body>
            <KatexMath latex="z_{\text{rate}} = \frac{x_t - \text{median}_{252d}}{1.4826 \times \text{MAD}_{252d}}" />

            <Body>
              <strong className="text-[var(--color-text)]">
                z_blended (M.3.2).
              </strong>{" "}
              60% tactical (252d) + 40% structural (2520d real 10Y) MAD Z-score.
              Tactical captures near-term momentum; structural captures secular
              valuation.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">
                Momentum check.
              </strong>{" "}
              Carry momentum <Mono>{"m = x_t - x_{t-20}"}</Mono> flags fading
              trends. When <Mono>z &gt;= 1.15</Mono> and{" "}
              <Mono>m &lt;= -0.25</Mono> simultaneously, the regime flips to{" "}
              <Mono>CARRY_COLLAPSE</Mono>.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">
                Policy-breakout override.
              </strong>{" "}
              If breakeven inflation moves <Mono>≥ 12 bps</Mono> in 5 days while{" "}
              <Mono>|z| ≥ 2.0</Mono>, the gate overrides to{" "}
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
                Adaptive precision weighting (M.2.1).
              </strong>{" "}
              Precision weights: static weights scaled by |Spearman beta| /
              0.10, floored at 10%. Signals with stronger historical predictive
              power receive higher effective weight.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">
                Redundancy penalty (M.2.2).
              </strong>{" "}
              0.03 per same-sign pair, capped at 0.15. Prevents overconfidence
              when correlated signals (rate + carry) align.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">
                Composite hysteresis.
              </strong>{" "}
              When no override fires, the composite score maps to a five-tier
              snap function with memory of yesterday's tier. Sequential
              evaluation — each condition tested in order:
            </Body>
            <Piecewise
              lhs={<>snap(c) =</>}
              cases={[
                ["4", "if c > 1.0"],
                ["3", "if c > 0.4"],
                ["2", "if c ≥ −0.4"],
                ["1", "if c ≥ −1.0"],
                ["0", "otherwise"],
              ]}
            />
            <Body>
              Tier changes of two or more steps are immediate. Single-step
              changes deferred by tighter hold thresholds:
            </Body>
            <div className="font-mono text-[11px] text-[var(--color-text-secondary)] leading-relaxed mb-6 border border-[var(--color-border)] bg-[var(--color-elevated)] p-4">
              <div className="grid grid-cols-[1fr_auto] gap-x-6 gap-y-1">
                <span>Tier 4 (strong bull) hold</span>
                <span className="text-[var(--color-text)]">c ≥ 0.85</span>
                <span>Tier 3 (bull) hold</span>
                <span className="text-[var(--color-text)]">c ≥ 0.28</span>
                <span>Tier 2 (neutral) hold</span>
                <span className="text-[var(--color-text)]">|c| &lt; 0.15</span>
                <span>Tier 1 (bear) hold</span>
                <span className="text-[var(--color-text)]">c ≤ −0.28</span>
                <span>Tier 0 (strong bear) hold</span>
                <span className="text-[var(--color-text)]">c ≤ −0.85</span>
              </div>
            </div>
            <Body>
              Invalidation by stale or missing data forces neutral fallback. A{" "}
              <Mono>structural_instability</Mono> flag triggers{" "}
              <Mono>CARRY_COLLAPSE</Mono> before all other checks.
            </Body>
          </Subsection>

          {/* ── Layer 2 ─────────────────────────────────────────────── */}
          <Subsection
            title="Layer 2 — Directional Bias & Conviction"
            id="layer2"
          >
            <Body>
              Layer 2 translates the gate's macro read into a discrete
              directional bias (LONG / SHORT / NEUTRAL) and a calibrated
              probability conviction <Mono>0.0–1.0</Mono>.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">
                Positioning percentile.
              </strong>{" "}
              CFTC non-commercial net positions are ranked over a 156-week
              lookback. The percentile <Mono>π</Mono> feeds three metrics:
            </Body>
            <KatexMath latex="\phi_{\text{upper}}(\pi) = \max(0, \min(1, \frac{\pi - 90}{10})) \quad \phi_{\text{lower}}(\pi) = \max(0, \min(1, \frac{10 - \pi}{10}))" />
            <Body>
              <strong className="text-[var(--color-text)]">
                COT smart spread (M.3.3).
              </strong>{" "}
              70% traditional non-commercial net-long percentile + 30%
              (asset-manager minus leveraged-money) spread. Reduces noise from
              speculator repositioning.
            </Body>

            <Body>
              Crowding flag: <Mono>π ≥ 90</Mono> or <Mono>π ≤ 10</Mono>.
              Crowding veto: <Mono>π ≥ 97</Mono> or <Mono>π ≤ 3</Mono>.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">
                Marcus B clash veto.
              </strong>{" "}
              If the rate sign and positioning sign point in opposite directions
              (both materially non-zero, with a <Mono>±5 pp</Mono> deadband
              around the 50th percentile), the bias is forced to NEUTRAL and
              conviction is capped at 0.50.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">
                Marcus C composite-rate clash.
              </strong>{" "}
              If the composite score and rate direction strongly disagree{" "}
              <Mono>(|S| &gt; 0.30)</Mono>, the bias is forced to NEUTRAL and
              conviction is capped at 0.50. This prevents the rate signal from
              overriding a divergent composite.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">
                Conviction multiplier.
              </strong>{" "}
              Alignment bonus when rate and positioning agree; penalty when they
              conflict or when crowding is elevated. If positioning data is
              missing, an additional <Mono>0.88</Mono> discount applies:
            </Body>
            <KatexMath latex="m_{\pi} = \max(0.52, \min(1.08, \; (1 - 0.48 \cdot p_{\text{crowd}}) \cdot a_{\text{align}} \;))" />
            <Body>
              where <Mono>a = 1.0</Mono> if rate and positioning agree,{" "}
              <Mono>0.72</Mono> if they conflict. The effective rate sign uses a
              tactical z-score when informative <Mono>{"(|z| > 0.12);"}</Mono>{" "}
              otherwise it falls back to the futures-style BULLISH/BEARISH
              label.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">
                Conviction score.
              </strong>{" "}
              Base conviction is anchored to the composite magnitude, then
              scaled by <Mono>m_π</Mono>. The raw score is an integer{" "}
              <Mono>1–5</Mono> which is then divided by 5 and stored as a
              probability <Mono>0.0–1.0</Mono>:
            </Body>
            <KatexMath latex="C = \frac{1}{5} \cdot \text{round}\Big( \max(1, \min(5, \; (3 + \text{clip}(S, -2, 2)) \cdot m_{\pi} \;)) \Big)" />
            <Body>
              Direction logic: if the composite is materially non-zero{" "}
              <Mono>(|S| &gt; 0.30)</Mono>, composite drives the bias; otherwise
              the rate sign drives it. If Layer 1 is invalidated, crowding is
              veto-level, or Marcus B / Marcus C clashes fire, the bias is
              forced to NEUTRAL and conviction is hard-capped at 0.50.
            </Body>
          </Subsection>

          {/* ── Layer 3 ─────────────────────────────────────────────── */}
          <Subsection title="Layer 3 — Execution & Timing" id="layer3">
            <Body>
              Layer 3 produces entry timing (ENTER / WAIT), position sizing
              (FULL / HALF), and stop levels from realized volatility, risk
              reversal skew, and intraday microstructure.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">
                Realized-vol rank.
              </strong>{" "}
              The 21-day annualized realized vol is scored against its empirical
              CDF over a trailing 3-year (756 session) causal window. Let{" "}
              <Mono>q^σ_t</Mono> denote the quantile. Entry is blocked when{" "}
              <Mono>q^σ_t {" > 0.88"}</Mono>. Full size requires{" "}
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
              <Mono>(|z| {" > 0.35"})</Mono>.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">
                Marcus enter rule.
              </strong>{" "}
              Entry requires: bias ≠ NEUTRAL, conviction ≥ 0.50,{" "}
              <Mono>q^σ_t ≤ 0.88</Mono>, no skew reversal, and no strong
              directional skew contradiction. A strong contradiction fires when{" "}
              skew alignment <Mono>A_t = −1</Mono>, <Mono>|z_t| &gt; 1.0</Mono>,
              and conviction <Mono>&lt; 0.75</Mono> — the disagreement is too
              large to absorb.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">
                Lena + Chen sizing.
              </strong>{" "}
              Full size only when: timing = ENTER, conviction ≥ 0.75,{" "}
              <Mono>q^σ_t ≤ 0.70</Mono>, skew alignment ≥ 0, and no Chen trim.
              Chen trim fires when the crowding flag is active{" "}
              <Mono>(π ≥ 90</Mono> or <Mono>π ≤ 10)</Mono> or when the crowding
              penalty <Mono>p_crowd &gt; 0.35</Mono>. Otherwise HALF.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">Stop level.</strong>{" "}
              Stop buffer is <Mono>max(1.5 · ADR_20, MIE_proxy)</Mono> where ADR
              is the mean daily range and MIE proxy is the worst adverse
              intraday move from the open against the directional bias over 20
              days:
            </Body>
            <Piecewise
              lhs={<>Stop =</>}
              cases={[
                ["Sₜ − buffer", "LONG"],
                ["Sₜ + buffer", "SHORT"],
                ["none", "NEUTRAL"],
              ]}
            />
          </Subsection>

          {/* ── Signal Decomposition ────────────────────────────────── */}
          <SignalDecomposition />

          {/* ── Per-Pair Differences ────────────────────────────────── */}
          <Subsection title="Per-Pair Methodology" id="per-pair">
            <Body>
              The three pairs share the same three-layer architecture but differ
              in weighting, data sources, and special-signal handling.
            </Body>

            {/* EURUSD */}
            <div className="mb-8">
              <h3 className="font-sans font-semibold text-lg text-[var(--color-text)] tracking-tight mb-3 flex items-center">
                <PairDot color={pairMap.EURUSD} />
                EUR / USD
              </h3>
              <Body>
                Primary driver is the US–Germany 2-year yield spread (FRED{" "}
                <Mono>DGS2</Mono> vs ECB data-api). Composite weights: rate{" "}
                differential <Mono>~45%</Mono>, COT positioning{" "}
                <Mono>~25%</Mono>, realized volatility <Mono>~20%</Mono>, open
                interest <Mono>~5%</Mono>, special signal <Mono>~5%</Mono>. The
                special signal blends Bund-BTP spread (Italian sovereign stress
                percentile) with ECB balance sheet YoY growth rate. Computed as
                dual-horizon MAD Z-score. Risk-reversal skew is monitored but
                not used as a composite modifier.
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
                <Mono>DGS2</Mono> vs MOF JGBs). Composite weights: rate{" "}
                differential <Mono>~40%</Mono>, COT positioning{" "}
                <Mono>~20%</Mono>, realized volatility <Mono>~25%</Mono>, open
                interest <Mono>~5%</Mono>, special signal <Mono>~10%</Mono>. The
                special signal is a VIX funding-stress proxy: high VIX → JPY bid
                → USD weakness. Carry-trade dynamics are explicitly monitored —
                when carry risk-adjusted z-score is elevated (≥ 1.15) but 20-day
                momentum is fading (≤ −0.25), the gate triggers{" "}
                <Mono>CARRY_COLLAPSE</Mono>. Confidence receives a +5 pp bonus
                when the special signal <Mono>{" > 0.5"}</Mono>.
              </Body>
            </div>

            {/* USDINR */}
            <div className="mb-8">
              <h3 className="font-sans font-semibold text-lg text-[var(--color-text)] tracking-tight mb-3 flex items-center">
                <PairDot color={pairMap.USDINR} />
                USD / INR
              </h3>
              <Body>
                INR uses a tailored composite with reduced COT weight. Composite
                weights: rate differential <Mono>~30%</Mono>, COT{" "}
                <Mono>~10%</Mono>, realized volatility <Mono>~20%</Mono>, open
                interest <Mono>~5%</Mono>, special signal <Mono>~20%</Mono>, FPI
                flow <Mono>~15%</Mono>. COT is a reduced-weight proxy
                (managed-float positioning is less informative than major
                floating-rate FX). The special signal blends crude oil and DXY
                pressure on EMFX (40% oil + 35% DXY + 25% EM composite). FPI is
                SEBI daily net flow z-scored over 20 days. When Brent is above
                its 80th percentile, confidence receives a −5 pp adjustment
                reflecting external-account vulnerability.
              </Body>
            </div>
          </Subsection>

          {/* ── Confidence ──────────────────────────────────────────── */}
          <Subsection title="Confidence Derivation" id="confidence">
            <Body>
              Confidence is not a probability of being correct. It is an
              internal consistency metric: signal strength modulated by
              directional agreement, pair-specific adjustments, and an
              institutional −3 pp haircut.
            </Body>

            <Body>
              Base confidence is driven by the absolute composite magnitude. The
              composite is clipped to <Mono>[−2, 2]</Mono> upstream; typical
              range is <Mono>[−1, 1]</Mono>:
            </Body>
            <KatexMath latex="\text{base} = \text{clip}\left(\frac{|S|}{2.0}, \; 0.10, \; 0.90\right)" />

            <Body>
              <strong className="text-[var(--color-text)]">
                Agreement bonus.
              </strong>{" "}
              +5 pp if rate and COT point in the same direction. Additional +5
              pp if both have magnitude {" > 0.3"}.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">
                Pair adjustments.
              </strong>{" "}
              USDJPY special signal {" > 0.5"} adds +5 pp. USDINR Brent above
              80th percentile subtracts −5 pp. Other pairs have their own
              commodity / special-signal adjustments.
            </Body>

            <Body>
              Raw confidence is clipped to <Mono>[0.30, 0.95]</Mono>, then the
              institutional haircut is applied:
            </Body>
            <KatexMath latex="C_{\text{raw}} = \text{clip}\left( \text{clip}(\text{base} + \text{bonus} + \text{pair}, \; 0.30, \; 0.95) - 0.03, \; 0.30, \; 0.90 \right)" />

            <Body>
              <strong className="text-[var(--color-text)]">
                Platt calibration.
              </strong>{" "}
              Calibrated confidence applies Platt scaling:
            </Body>
            <KatexMath latex="C_{\text{calibrated}} = 0.35 + 0.40 \times C_{\text{raw}}" />
            <Body>
              Max calibrated confidence ≈ 0.71 even if raw reaches 0.90.
            </Body>
          </Subsection>

          {/* ── Validation Methodology ──────────────────────────────── */}
          <Subsection title="Validation Methodology" id="validation">
            <Body>
              Every regime call is validated out-of-sample at two horizons: T+5
              (one trading week) and T+20 (one trading month). Validation is
              append-only; once written, a validation row is never mutated.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">
                Directional outcome.
              </strong>{" "}
              The log-return in basis points between call-date spot and
              horizon-date spot is:
            </Body>
            <KatexMath latex="r_{h} = 10{,}000 \cdot \ln\left(\frac{S_{t+h}}{S_t}\right)" />
            <Body>
              A 5 bps dead-band filters noise: UP if <Mono>r {" > 5"}</Mono>,
              DOWN if <Mono>r {" < -5"}</Mono>, otherwise NEUTRAL.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">Correctness.</strong>{" "}
              A BULLISH call is correct only if realized is UP; BEARISH only if
              DOWN; NEUTRAL only if realized is NEUTRAL.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">Brier score.</strong>{" "}
              For each directional call (non-neutral), the Brier score is{" "}
              <Mono>(p − y)²</Mono> where <Mono>p</Mono> is the confidence and{" "}
              <Mono>y = 1</Mono> if correct, <Mono>0</Mono> otherwise. The
              random-guess baseline for three outcomes is <Mono>0.333</Mono>.
              Brier score (heuristic confidence) is reported as{" "}
              <Mono>(baseline − mean) / baseline</Mono>.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">Win rate.</strong>{" "}
              Computed only over directional calls (excludes neutral) to avoid
              inflating accuracy with no-trade states.
            </Body>
          </Subsection>

          {/* ── Regime Validation via Sizing Simulation ─────────────── */}
          <Subsection
            title="Regime Validation via Sizing Simulation"
            id="simulation"
          >
            <Body>
              The core question is not whether the model generates positive
              returns, but whether regime conviction improves risk-adjusted
              returns versus a uniform benchmark. This is a validation exercise,
              not a trading strategy.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">
                Uniform benchmark.
              </strong>{" "}
              Every directional call receives identical exposure sizing
              regardless of confidence. This produces a baseline return series
              that isolates the value of directional accuracy alone.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">
                Regime-aware sizing.
              </strong>{" "}
              Exposure scales with calibrated confidence. Higher-confidence
              calls receive larger sizing; lower-confidence calls receive
              smaller sizing. Neutral calls receive zero exposure. The scaling
              function is sigmoid-clipped to prevent over-concentration in any
              single call.
            </Body>

            <Body>
              <strong className="text-[var(--color-text)]">
                Why this validates regime labels.
              </strong>{" "}
              If regime-aware sizing produces a higher Sharpe ratio, higher
              Sortino, and lower maximum drawdown than uniform sizing — using
              the exact same directional calls — then the regime labels are
              adding genuine information beyond random directional bias. If not,
              the labels are noise and the framework requires revision.
            </Body>

            <Body>
              The comparison is reported on the Track Record page under the
              "Regime Validation" tab: Sharpe, Sortino, max drawdown,
              return-to-drawdown ratio, hit rate by confidence decile, and
              regime-conditional performance breakdown.
            </Body>
          </Subsection>

          {/* ── Data Sources ────────────────────────────────────────── */}
          <Subsection title="Data Sources & Fallback Chain" id="data-sources">
            <Body>
              All data is fetched daily via an async ingestion engine with
              explicit backoff and retry. Missing primary sources trigger a
              documented fallback chain; if all fail, the signal is marked stale
              rather than interpolated.
            </Body>

            <div className="border border-[var(--color-border)] mb-6 overflow-x-auto">
              <table className="w-full border-collapse font-mono text-[11px] min-w-[600px]">
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
                    [
                      "Risk Reversal",
                      "Pending real OTC data (synthetic proxy removed v2.1)",
                      "—",
                    ],
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
                    ["Weight", "30–45% (pair-specific)"],
                  ],
                },
                {
                  label: "COT Positioning",
                  desc: "CFTC weekly non-commercial net positions as 156-week percentile ranks.",
                  stats: [
                    ["Source", "CFTC Disaggregated"],
                    ["Lag", "3 days"],
                    ["Weight", "10–25% (pair-specific)"],
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
                  label: "Open Interest",
                  desc: "CME futures OI delta and price-alignment flag.",
                  stats: [
                    ["OI source", "CME daily CSV"],
                    ["Products", "6E, 6J"],
                    ["Unwind flag", "Crowded COT + 3d shrinking OI"],
                    ["Weight", "5% (explicit, all pairs)"],
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
                Regime Thresholds (EUR/USD, USD/JPY)
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

            <div className="mt-6 pt-6 border-t border-[var(--color-border)]">
              <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-4">
                Regime Thresholds (USD/INR)
              </p>
              <div className="flex flex-col gap-2 font-mono text-[10px]">
                {[
                  ["INR_DEPRECIATION_STRONG", "S > +1.0"],
                  ["INR_DEPRECIATION_MODERATE", "+0.4 < S ≤ +1.0"],
                  ["INR_NEUTRAL", "−0.4 ≤ S ≤ +0.4"],
                  ["INR_APPRECIATION_MODERATE", "−1.0 ≤ S < −0.4"],
                  ["INR_APPRECIATION_STRONG", "S < −1.0"],
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

            <div className="mt-6 pt-6 border-t border-[var(--color-border)]">
              <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-4">
                Volatility Overlay
              </p>
              <p className="font-sans text-[12px] text-[var(--color-text-secondary)] leading-relaxed">
                When realized-vol rank exceeds the 88th percentile, the regime
                label appends <Mono>__VOL_EXPANDING</Mono> to the neutral tier.
                This flags elevated volatility without changing the directional
                read.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Known Weaknesses ─────────────────────────────────────────── */}
      <div className="reveal mb-12 mt-16 px-6 py-6 bg-[var(--color-surface)] border border-[var(--color-brand-amber)]/30">
        <p className="font-mono text-[10px] tracking-[0.2em] text-[var(--color-brand-amber)] uppercase mb-4">
          Known Weaknesses
        </p>
        <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] mb-4">
          We believe methodology pages should be honest about limitations, not
          just strengths. Here is what is currently imperfect:
        </p>
        <div className="space-y-4">
          <div>
            <p className="font-sans font-semibold text-[14px] text-[var(--color-text)] mb-1">
              Risk Reversal — Pending Real Data
            </p>
            <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-[1.6]">
              We do not yet have access to real 25-delta risk reversal data. Our
              Layer 3 execution currently operates without skew information. We
              are sourcing OTC options data for v3.0.
            </p>
          </div>
          <div>
            <p className="font-sans font-semibold text-[14px] text-[var(--color-text)] mb-1">
              Signal Weights — Heuristic
            </p>
            <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-[1.6]">
              Weights are heuristic round numbers (e.g., Rate 45%, COT 25%)
              based on macro intuition. They have not been walk-forward
              optimized. v3.0 will replace these with ICIR-based dynamic
              weights.
            </p>
          </div>
          <div>
            <p className="font-sans font-semibold text-[14px] text-[var(--color-text)] mb-1">
              Confidence Scores — Uncalibrated
            </p>
            <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-[1.6]">
              Confidence is a heuristic consistency metric, not a calibrated
              probability. A 70% confidence does NOT mean a 70% chance of being
              correct. Proper isotonic calibration is under development for
              v3.0.
            </p>
          </div>
          <div>
            <p className="font-sans font-semibold text-[14px] text-[var(--color-text)] mb-1">
              Layer 1 Thresholds — Ad-Hoc
            </p>
            <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-[1.6]">
              Regime gate thresholds (e.g., Z &gt; 2.0, Δπ &gt; 0.12) were set
              by inspection, not systematic optimization. v3.0 will replace
              these with a Hidden Markov Model.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
