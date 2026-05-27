import { Footer } from "@/components/shell/Footer";
import { Nav } from "@/components/shell/Nav";
import { AuditTrailBannerServer } from "@/components/ui/audit-trail-banner";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Our Journey | FX Regime Lab",
  description:
    "FX Regime Lab is not a product. It is an experiment in transparent macro research. Here is how we got here, and where we are going.",
};

const timeline = [
  {
    version: "v0.1",
    date: "February 2026",
    title: "The Spark",
    description:
      "Built the first Python script to scrape CFTC COT data and compute net positioning percentiles. A single Jupyter notebook. No frontend. No database.",
    status: "done",
  },
  {
    version: "v0.5",
    date: "February 2026",
    title: "First Composite",
    description:
      "Combined rate differentials and COT into a weighted composite score. Manual Excel tracking. First realization that static weights felt arbitrary.",
    status: "done",
  },
  {
    version: "v1.0",
    date: "March 2026",
    title: "The Pipeline",
    description:
      "Built the first automated pipeline with Prefect. Added vol, OI, and cross-asset signals. Supabase backend. Still no public frontend.",
    status: "done",
  },
  {
    version: "v1.5",
    date: "March 2026",
    title: "Web Terminal",
    description:
      "Launched the first web interface. Added track record visualization, daily briefs, and desk open cards. Still learning that our accuracy was near-random.",
    status: "done",
  },
  {
    version: "v2.0",
    date: "April 2026",
    title: "Three-Layer Engine",
    description:
      "Introduced Layer 1 (structural gate), Layer 2 (directional conviction), and Layer 3 (execution HUD). Added hysteresis, Marcus clash logic, and confidence scoring. First SSRN paper draft.",
    status: "done",
  },
  {
    version: "v2.1",
    date: "May 2026",
    title: "Radical Honesty",
    description:
      "Before public launch, we conducted a deep mathematical audit. Discovered that our confidence scores were not probabilities, our RR proxy was synthetic, and our accuracy was statistically indistinguishable from random. Rather than hide this, we published our limitations openly.",
    status: "current",
  },
  {
    version: "v3.0",
    date: "July 2026 (Planned)",
    title: "Proper Probabilities",
    description:
      "Isotonic regression calibration for confidence scores. Real 25Δ risk reversal data. Bayesian dynamic betas via Kalman filter. Walk-forward ICIR weight optimization. Hidden Markov Model for regime detection. This is when the signal architecture becomes statistically defensible.",
    status: "planned",
  },
  {
    version: "v3.5",
    date: "August 2026 (Planned)",
    title: "Expand the Universe",
    description:
      "Add GBP/USD, AUD/USD, USD/CAD, USD/CHF as active pairs. Each pair will require its own calibrated model and weight optimization.",
    status: "planned",
  },
  {
    version: "v4.0",
    date: "2027 (Vision)",
    title: "The Open Standard",
    description:
      "Publish the full methodology as an open standard. Invite external auditors. Host a public model competition. Prove that transparent macro research can be conducted at institutional standards without institutional budgets.",
    status: "vision",
  },
];

export default function JourneyPage() {
  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      <Nav />
      <AuditTrailBannerServer variant="shell" />
      <main
        id="main-content"
        className="max-w-[1152px] mx-auto px-6 pt-28 pb-20 w-full"
      >
        <div className="max-w-[800px] mx-auto">
          <span className="block font-sans text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-6">
            FX Regime Lab
          </span>
          <h1 className="font-serif font-light text-[clamp(32px,5vw,48px)] text-[var(--color-text)] leading-[1.15] tracking-tight mb-4">
            Our Journey
          </h1>
          <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] mb-16 max-w-[600px]">
            FX Regime Lab is not a product. It is an experiment in transparent
            macro research. Here is how we got here, and where we are going.
          </p>

          <div className="relative border-l border-[var(--color-border)] ml-3">
            {timeline.map((item) => (
              <div key={item.version} className="mb-12 ml-8 relative">
                <div
                  className={[
                    "absolute -left-[37px] w-3 h-3 rounded-full border-2",
                    item.status === "done"
                      ? "bg-[var(--color-brand-amber)] border-[var(--color-brand-amber)]"
                      : "",
                    item.status === "current"
                      ? "bg-[var(--color-brand-amber)] border-[var(--color-brand-amber)] animate-pulse"
                      : "",
                    item.status === "planned"
                      ? "bg-[var(--color-text-muted)] border-[var(--color-text-muted)]"
                      : "",
                    item.status === "vision"
                      ? "bg-transparent border-dashed border-[var(--color-text-muted)]"
                      : "",
                  ].join(" ")}
                />
                <div className="font-sans text-[11px] tracking-[0.1em] text-[var(--color-text-muted)] mb-1">
                  {item.version} — {item.date}
                </div>
                <h3 className="font-sans font-semibold text-[16px] text-[var(--color-text)] mb-2">
                  {item.title}
                </h3>
                <p className="font-sans text-[14px] text-[var(--color-text-secondary)] leading-[1.7]">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
