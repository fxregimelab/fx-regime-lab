import { createClient } from "@/lib/supabase/server";
import {
  getLatestRegimeCalls,
  getLatestSignals,
  getValidationLog,
} from "@/lib/supabase/queries";
import { PAIRS } from "@/lib/constants";
import { Nav } from "@/components/shell/Nav";
import { Footer } from "@/components/shell/Footer";
import Link from "next/link";

/* ------------------------------------------------------------------ */
/*  Reusable section heading                                           */
/* ------------------------------------------------------------------ */
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-4">
      {children}
    </p>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="font-sans font-semibold text-[28px] text-[var(--color-text)] tracking-tight leading-snug">
      {children}
    </h2>
  );
}

/* ------------------------------------------------------------------ */
/*  Hero                                                               */
/* ------------------------------------------------------------------ */
function Hero() {
  return (
    <section className="min-h-[92vh] flex flex-col justify-center relative">
      <div className="max-w-[1152px] mx-auto px-6 w-full">
        <div className="max-w-[640px]">
          <div className="flex items-center gap-3 mb-8 animate-fade-in">
            <span className="w-2 h-2 rounded-full bg-[var(--color-up)] animate-gentle-pulse" />
            <span className="font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase">
              Live · G10 FX · Daily Calls
            </span>
          </div>

          <h1 className="font-sans font-semibold text-[clamp(40px,6vw,72px)] text-[var(--color-text)] leading-[1.08] tracking-tight mb-7 animate-fade-up delay-100">
            Daily regime
            <br />
            calls. On the
            <br />
            record.
          </h1>

          <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] max-w-[440px] mb-10 animate-fade-up delay-200">
            G10 FX regime classification across EUR/USD, USD/JPY, and USD/INR.
            Composite signal from rate differentials, COT positioning, realized
            volatility, and open interest. Every call public before market open.
            Every outcome validated.
          </p>

          <div className="flex gap-4 items-center animate-fade-up delay-300">
            <Link
              href="/brief"
              className="px-6 py-2.5 bg-[var(--color-text)] text-[var(--color-void)] font-sans text-[13px] tracking-wide transition-all duration-300 hover:bg-[var(--color-accent-hover)]"
            >
              Read today&apos;s brief
            </Link>
            <Link
              href="/terminal"
              className="font-sans text-[13px] text-[var(--color-text-muted)] underline decoration-[var(--color-border)] underline-offset-4 transition-colors duration-300 hover:text-[var(--color-text)]"
            >
              Open terminal →
            </Link>
          </div>
        </div>
      </div>

      {/* Scroll hint */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 animate-fade-in delay-700">
        <span className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
          Scroll
        </span>
        <div className="w-px h-8 bg-gradient-to-b from-[var(--color-text-muted)] to-transparent" />
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  Live snapshot cards                                                */
/* ------------------------------------------------------------------ */
function SnapshotCard({
  pair,
  spot,
  regime,
  confidence,
  delay,
}: {
  pair: string;
  spot: string;
  regime: string;
  confidence: number;
  delay: number;
}) {
  return (
    <div
      className="reveal border border-[var(--color-border)] bg-[var(--color-surface)] p-6 hover-lift transition-all duration-500"
      style={{ transitionDelay: `${delay}ms` }}
    >
      <div className="flex items-baseline justify-between mb-6">
        <span className="font-mono text-[11px] tracking-[0.15em] text-[var(--color-text-secondary)] uppercase font-medium">
          {pair}
        </span>
        <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
          Spot
        </span>
      </div>

      <p className="font-mono text-[32px] font-medium text-[var(--color-text)] tracking-tight leading-none mb-6 tabular-nums">
        {spot}
      </p>

      <div className="mb-4">
        <p className="font-mono text-[11px] font-medium text-[var(--color-text-secondary)] tracking-wide leading-snug mb-1">
          {regime}
        </p>
      </div>

      <div className="pt-4 border-t border-[var(--color-border)]">
        <div className="flex items-center justify-between mb-2">
          <span className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
            Confidence
          </span>
          <span className="font-mono text-[13px] text-[var(--color-text-secondary)] font-medium">
            {Math.round(confidence * 100)}%
          </span>
        </div>
        <div className="h-[2px] bg-[var(--color-border)] overflow-hidden">
          <div
            className="h-full bg-[var(--color-accent)] transition-all duration-1000 ease-out"
            style={{ width: `${confidence * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
}

function LiveSnapshot({
  calls,
  signals,
}: {
  calls: Awaited<ReturnType<typeof getLatestRegimeCalls>>;
  signals: Awaited<ReturnType<typeof getLatestSignals>>;
}) {
  return (
    <section className="py-24">
      <div className="max-w-[1152px] mx-auto px-6">
        <div className="reveal mb-14">
          <SectionLabel>Live Snapshot</SectionLabel>
          <div className="flex items-end justify-between flex-wrap gap-4">
            <SectionTitle>Today&apos;s regime calls</SectionTitle>
            <Link
              href="/terminal"
              className="font-sans text-[13px] text-[var(--color-text-muted)] underline decoration-[var(--color-border)] underline-offset-4 transition-colors duration-300 hover:text-[var(--color-text)]"
            >
              Open full terminal →
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {PAIRS.map((pair, i) => {
            const call = calls[pair.label];
            const signal = signals[pair.label];
            return (
              <SnapshotCard
                key={pair.label}
                pair={pair.display}
                spot={signal?.spot?.toFixed(4) ?? "—"}
                regime={call?.regime ?? "—"}
                confidence={call?.confidence ?? 0}
                delay={(i + 1) * 100}
              />
            );
          })}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  Signal architecture                                                */
/* ------------------------------------------------------------------ */
function SignalArchitecture() {
  const signals = [
    {
      n: "01",
      label: "Rate Differentials",
      desc: "2Y sovereign yield spreads. Primary driver of medium-term FX regime direction.",
      weight: "~40%",
    },
    {
      n: "02",
      label: "COT Positioning",
      desc: "CFTC weekly non-commercial net positions as percentile ranks. Crowd and reversal signals.",
      weight: "~30%",
    },
    {
      n: "03",
      label: "Realized Volatility",
      desc: "5d and 20d realized vs 30d implied. Vol gate forces elevation above 90th percentile.",
      weight: "~20%",
    },
    {
      n: "04",
      label: "OI and Risk Reversals",
      desc: "Open interest flows and 25-delta risk reversals. INR-specific series included.",
      weight: "~10%",
    },
  ];

  return (
    <section className="py-24 bg-[var(--color-elevated)]">
      <div className="max-w-[1152px] mx-auto px-6">
        <div className="reveal mb-14">
          <SectionLabel>Signal Architecture</SectionLabel>
          <SectionTitle>
            Four signal families.
            <br />
            One composite.
          </SectionTitle>
          <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] max-w-[480px] mt-4">
            Each family is normalized to a percentile rank before weighting. The
            composite drives the regime label.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-[var(--color-border)] border border-[var(--color-border)]">
          {signals.map((s, i) => (
            <div
              key={s.n}
              className="reveal bg-[var(--color-surface)] p-8 transition-all duration-500"
              style={{ transitionDelay: `${(i + 1) * 100}ms` }}
            >
              <div className="flex items-start justify-between mb-6">
                <span className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)]">
                  {s.n}
                </span>
                <span className="font-mono text-[10px] tracking-[0.1em] text-[var(--color-text-muted)]">
                  {s.weight}
                </span>
              </div>
              <h3 className="font-sans font-semibold text-[15px] text-[var(--color-text)] mb-2">
                {s.label}
              </h3>
              <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-[1.6]">
                {s.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  Validation trust strip                                             */
/* ------------------------------------------------------------------ */
function ValidationTrust({
  accuracy,
  totalCalls,
}: {
  accuracy: number;
  totalCalls: number;
}) {
  const stats = [
    { label: "Pairs tracked", value: String(PAIRS.length) },
    { label: "Calls since April 2026", value: String(totalCalls) },
    { label: "Accuracy", value: `${accuracy.toFixed(1)}%` },
    { label: "Signal families", value: "4" },
  ];

  return (
    <section className="py-24">
      <div className="max-w-[1152px] mx-auto px-6">
        <div className="reveal mb-14">
          <SectionLabel>Validation</SectionLabel>
          <SectionTitle>Every call validated. No ex-post edits.</SectionTitle>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[var(--color-border)] border border-[var(--color-border)] mb-12">
          {stats.map((s, i) => (
            <div
              key={s.label}
              className="reveal bg-[var(--color-surface)] p-6 transition-all duration-500"
              style={{ transitionDelay: `${(i + 1) * 100}ms` }}
            >
              <p className="font-mono text-[clamp(24px,3vw,32px)] font-medium text-[var(--color-text)] tracking-tight leading-none mb-2 tabular-nums">
                {s.value}
              </p>
              <p className="font-mono text-[9px] tracking-[0.12em] text-[var(--color-text-muted)] uppercase">
                {s.label}
              </p>
            </div>
          ))}
        </div>

        <div className="reveal flex items-center justify-between flex-wrap gap-4 pt-6 border-t border-[var(--color-border)]">
          <p className="font-sans text-[13px] text-[var(--color-text-secondary)]">
            Outcomes measured against next-day spot with a 5bps dead-band. Brier
            scores computed for directional calls.
          </p>
          <Link
            href="/performance"
            className="font-sans text-[13px] text-[var(--color-text-muted)] underline decoration-[var(--color-border)] underline-offset-4 transition-colors duration-300 hover:text-[var(--color-text)]"
          >
            View full ledger →
          </Link>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  About snippet                                                      */
/* ------------------------------------------------------------------ */
function AboutSnippet() {
  return (
    <section className="py-24 bg-[var(--color-elevated)]">
      <div className="max-w-[1152px] mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-16 items-start">
          <div className="reveal">
            <SectionLabel>About</SectionLabel>
            <h3 className="font-sans font-semibold text-[22px] text-[var(--color-text)] tracking-tight leading-snug">
              Shreyash Sakhare
            </h3>
            <p className="font-mono text-[11px] text-[var(--color-text-muted)] mt-2 tracking-wide">
              EE Undergrad · Discretionary Macro Research
            </p>
          </div>

          <div className="reveal">
            <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] max-w-[560px] mb-6">
              Studying how G10 FX regimes form and break using rate
              differentials, COT positioning, and volatility. This site is the
              public trace of that work — dated calls, validated outcomes, no
              narrative added after the fact.
            </p>
            <div className="flex gap-5">
              <Link
                href="/about"
                className="px-5 py-2 border border-[var(--color-border)] font-sans text-[13px] text-[var(--color-text-secondary)] transition-all duration-300 hover:bg-[var(--color-text)] hover:text-[var(--color-void)] hover:border-[var(--color-text)]"
              >
                About this project
              </Link>
              <Link
                href="/methodology"
                className="font-sans text-[13px] text-[var(--color-text-muted)] underline decoration-[var(--color-border)] underline-offset-4 transition-colors duration-300 hover:text-[var(--color-text)] py-2"
              >
                Methodology →
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */
export default async function HomePage() {
  const supabase = await createClient();

  const [calls, signals, validation] = await Promise.all([
    getLatestRegimeCalls(supabase),
    getLatestSignals(supabase),
    getValidationLog(supabase),
  ]);

  const { count } = await supabase
    .from("regime_calls")
    .select("*", { count: "exact", head: true });

  const correctCount = validation.filter((r) => r.outcome === "correct").length;
  const accuracy = validation.length > 0 ? (correctCount / validation.length) * 100 : 0;

  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      <Nav />
      <main>
        <Hero />
        <LiveSnapshot calls={calls} signals={signals} />
        <SignalArchitecture />
        <ValidationTrust accuracy={accuracy} totalCalls={count ?? 0} />
        <AboutSnippet />
      </main>
      <Footer />
    </div>
  );
}
