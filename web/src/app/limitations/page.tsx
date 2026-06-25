import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Limitations & Known Issues | FX Regime Lab",
  description:
    "We believe radical honesty builds better research. Here is everything that is currently imperfect in FX Regime Lab v2.1.",
};

export default function LimitationsPage() {
  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      <main id="main-content" className="pt-24 pb-24">
        <div className="max-w-[800px] mx-auto px-6">
          <span className="block font-sans text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-6">
            FX Regime Lab v2.1
          </span>
          <h1 className="font-serif font-light text-[clamp(32px,5vw,48px)] text-[var(--color-text)] leading-[1.15] tracking-tight mb-4">
            Limitations & Known Issues
          </h1>
          <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] mb-16 max-w-[600px]">
            We believe radical honesty builds better research. Here is
            everything that is currently imperfect in FX Regime Lab v2.1.
          </p>

          {/* Risk Reversal */}
          <section className="mb-14 border-l-2 border-[var(--color-brand-amber)] pl-6">
            <h2 className="font-sans font-semibold text-[18px] text-[var(--color-text)] mb-3">
              ⚠️ Risk Reversal Data is Synthetic
            </h2>
            <p className="font-sans text-[14px] text-[var(--color-text-secondary)] leading-[1.7] mb-3">
              Our 25-delta risk reversal signal is currently a proxy derived
              from daily price action, not actual options market data. We are
              actively sourcing real OTC risk reversal feeds. Until then, Layer
              3 execution skips skew-based rules entirely.
            </p>
            <p className="font-sans text-[12px] text-[var(--color-text-muted)]">
              Status: Sourcing real data. Expected: v3.0 (July 2026).
            </p>
          </section>

          {/* Confidence Scores */}
          <section className="mb-14 border-l-2 border-[var(--color-brand-amber)] pl-6">
            <h2 className="font-sans font-semibold text-[18px] text-[var(--color-text)] mb-3">
              ⚠️ Confidence Scores Are Not Probabilities
            </h2>
            <p className="font-sans text-[14px] text-[var(--color-text-secondary)] leading-[1.7] mb-3">
              The &quot;confidence&quot; score is a heuristic consistency
              metric, not a calibrated probability. A 60% confidence does NOT
              mean we believe the call has a 60% chance of being correct. We are
              building proper isotonic calibration for v3.0.
            </p>
            <p className="font-sans text-[12px] text-[var(--color-text-muted)]">
              Status: Calibration models under development. Expected: v3.0.
            </p>
          </section>

          {/* Weights */}
          <section className="mb-14 border-l-2 border-[var(--color-brand-amber)] pl-6">
            <h2 className="font-sans font-semibold text-[18px] text-[var(--color-text)] mb-3">
              ⚠️ Weights Are Heuristic, Not Optimized
            </h2>
            <p className="font-sans text-[14px] text-[var(--color-text-secondary)] leading-[1.7] mb-3">
              Signal weights (e.g., Rate 45%, COT 25%) are round-number
              heuristics based on macro intuition. They have not been
              walk-forward optimized. v3.0 will use ICIR-based dynamic weighting
              with purged cross-validation.
            </p>
          </section>

          {/* Accuracy */}
          <section className="mb-14 border-l-2 border-[var(--color-brand-amber)] pl-6">
            <h2 className="font-sans font-semibold text-[18px] text-[var(--color-text)] mb-3">
              ⚠️ Accuracy is Near Random
            </h2>
            <p className="font-sans text-[14px] text-[var(--color-text-secondary)] leading-[1.7] mb-3">
              Our T+5 directional accuracy is ~49% over the full backtested
              history (1997–2026). Live out-of-sample performance since May 2026
              is significantly lower (~15%) due to small sample size and recent
              market conditions. We publish both figures transparently because
              the goal is honest regime monitoring, not signals.
            </p>
          </section>

          {/* Transaction Costs */}
          <section className="mb-14 border-l-2 border-[var(--color-brand-amber)] pl-6">
            <h2 className="font-sans font-semibold text-[18px] text-[var(--color-text)] mb-3">
              ⚠️ Transaction Costs Not Included in Primary Metrics
            </h2>
            <p className="font-sans text-[14px] text-[var(--color-text-secondary)] leading-[1.7] mb-3">
              Track record shows gross returns. Typical FX spot bid-ask is
              0.1–1.0 bps for major FX and 5–20 bps for EM. Net returns may be
              substantially lower. We now report cost-adjusted metrics alongside
              gross.
            </p>
          </section>

          {/* Layer 1 Thresholds */}
          <section className="mb-14 border-l-2 border-[var(--color-brand-amber)] pl-6">
            <h2 className="font-sans font-semibold text-[18px] text-[var(--color-text)] mb-3">
              ⚠️ Layer 1 Thresholds Are Ad-Hoc
            </h2>
            <p className="font-sans text-[14px] text-[var(--color-text-secondary)] leading-[1.7] mb-3">
              Regime gate thresholds (e.g., Z &gt; 2.0, Δπ &gt; 0.12) were set
              by inspection, not systematic optimization. v3.0 will replace
              these with a Hidden Markov Model.
            </p>
          </section>

          {/* COT Staleness */}
          <section className="mb-14 border-l-2 border-[var(--color-brand-amber)] pl-6">
            <h2 className="font-sans font-semibold text-[18px] text-[var(--color-text)] mb-3">
              ⚠️ COT Data is Weekly, Treated as Daily
            </h2>
            <p className="font-sans text-[14px] text-[var(--color-text-secondary)] leading-[1.7] mb-3">
              CFTC Commitment of Traders reports weekly. Between publication
              dates, our model uses stale data. v2.1 tracks days-since-COT; v3.0
              will apply staleness decay.
            </p>
          </section>

          <div className="border border-[var(--color-border)] bg-[var(--color-surface)] p-6 mt-16">
            <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-[1.6]">
              If you find additional issues, please open a GitHub issue or email
              shreyash@fxregimelab.com. We will add them here with attribution.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
