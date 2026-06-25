import { Footer } from "@/components/shell/Footer";
import { Nav } from "@/components/shell/Nav";
import { ConfidenceMeter } from "@/components/ui/ConfidenceMeter";
import { MetricCard } from "@/components/ui/MetricCard";
import { RegimeBadge } from "@/components/ui/RegimeBadge";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { AuditTrailBannerServer } from "@/components/ui/audit-trail-banner";
import { ResearchDisclaimer } from "@/components/ui/research-disclaimer";
import { normalizeProp } from "@/components/ui/utils";
import { PAIRS } from "@/lib/constants";
import {
  getLatestBrief,
  getLatestRegimeCalls,
  getLatestSignals,
  getSiteContent,
  getValidationLog,
  getValidationStats,
} from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";
import type { Metadata } from "next";
import Link from "next/link";
import Script from "next/script";

export const revalidate = 3600;

export const metadata: Metadata = {
  title: "FX Regime Lab — Daily Regime Calls",
  description:
    "Open-source research infrastructure for transparent macro regime monitoring across major and EM FX. Every signal, every call, every mistake — published in real time.",
};

/* ─── Hero ──────────────────────────────────────────────────────────── */

function HeroSection({
  siteContent,
  latestCallDate,
}: {
  siteContent: Record<string, string>;
  latestCallDate: string | null;
}) {
  const headline =
    siteContent["hero.headline"] ?? "FX Regime Classification System";
  const subheadline =
    siteContent["hero.subheadline"] ??
    "Daily macro regime calls for EUR/USD, USD/JPY, and USD/INR.";
  const ctaPrimary = siteContent["hero.cta_primary"] ?? "Explore the Framework";
  const ctaSecondary =
    siteContent["hero.cta_secondary"] ?? "Explore the Framework";
  const principleQuote =
    siteContent["principle.quote"] ??
    "Credibility compounds through calendar discipline and honest validation, not marketing.";

  return (
    <section className="min-h-[90dvh] flex flex-col justify-center relative">
      <div className="max-w-[1152px] mx-auto px-6 w-full pt-24 pb-16">
        {/* Principle quote — serif, large, the emotional anchor */}
        <div className="mb-12 animate-fade-in">
          <span className="font-sans text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase block mb-6">
            FX Regime Lab
          </span>
          <blockquote
            className="font-serif font-light text-[clamp(28px,4.5vw,52px)] text-[var(--color-text)] leading-[1.2] tracking-tight max-w-[720px]"
            style={{
              fontFamily: "var(--font-playfair), ui-serif, Georgia, serif",
            }}
          >
            {principleQuote}
          </blockquote>
        </div>

        {/* Subheadline */}
        <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] max-w-[520px] mb-10 animate-fade-up delay-100">
          {subheadline}
        </p>

        {/* CTAs */}
        <div className="flex flex-wrap gap-4 mb-12 animate-fade-up delay-200">
          <Link
            href="/methodology"
            className="inline-block px-7 py-3.5 bg-[var(--color-brand-amber)] text-[var(--color-void)] font-sans text-[14px] font-medium tracking-[0.02em] transition-all duration-200 hover:brightness-110"
            style={{ borderRadius: 2 }}
          >
            Explore the Framework
          </Link>
          <Link
            href="/desk"
            className="inline-block px-7 py-3.5 border border-[var(--color-border)] font-sans text-[14px] text-[var(--color-text)] transition-all duration-200 hover:bg-[var(--color-surface)]"
            style={{ borderRadius: 2 }}
          >
            Open Terminal
          </Link>
        </div>

        {/* Status strip */}
        <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2 animate-fade-up delay-300">
          <div className="flex items-baseline gap-2">
            <span className="font-sans text-[11px] text-[var(--color-text-muted)]">
              Latest call
            </span>
            <span className="font-sans text-[11px] text-[var(--color-text)] tabular-nums">
              {latestCallDate ?? "—"}
            </span>
          </div>
          <span className="text-[var(--color-border)]">·</span>
          <div className="flex items-baseline gap-2">
            <span className="font-sans text-[11px] text-[var(--color-text-muted)]">
              3 pairs
            </span>
          </div>
          <span className="text-[var(--color-border)]">·</span>
          <div className="flex items-baseline gap-2">
            <span className="font-sans text-[11px] text-[var(--color-text-muted)]">
              T+5 / T+20 validation
            </span>
          </div>
          <span className="text-[var(--color-border)]">·</span>
          <div className="flex items-baseline gap-2">
            <span className="font-sans text-[11px] text-[var(--color-brand-amber)]">
              v2.1 Experimental
            </span>
          </div>
          <span className="text-[var(--color-border)]">·</span>
          <div className="flex items-baseline gap-2">
            <span className="font-sans text-[11px] text-[var(--color-text-muted)]">
              ~49% T+5 Accuracy
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── Live Snapshot Cards ───────────────────────────────────────────── */

function SnapshotCard({
  pair,
  pairColor,
  spot,
  regime,
  regimeCategory,
  confidence,
  date,
}: {
  pair: string;
  pairColor: string;
  spot: string;
  regime: string;
  regimeCategory?: string | null;
  confidence: number | null;
  date?: string;
}) {
  return (
    <div
      className="border border-[var(--color-border)] bg-[var(--color-surface)] p-6 hover-lift cursor-pointer glow-hover transition-all duration-500 relative"
      style={{ "--glow-color": `${pairColor}18` } as React.CSSProperties}
    >
      {/* Pair-colored top border */}
      <div
        className="absolute top-0 left-0 right-0 h-[2px]"
        style={{ backgroundColor: pairColor }}
      />
      <div className="flex items-baseline justify-between mb-5">
        <span
          className="font-sans text-[11px] tracking-[0.15em] uppercase font-semibold"
          style={{ color: pairColor }}
        >
          {pair}
        </span>
        <span className="font-sans text-[10px] text-[var(--color-text-muted)]">
          {date ?? "Spot"}
        </span>
      </div>

      <p className="font-sans text-[28px] font-semibold text-[var(--color-text)] tracking-tight leading-none mb-5 tabular-nums">
        {spot}
      </p>

      <div className="mb-4">
        <RegimeBadge
          regime={regime}
          category={regimeCategory ?? undefined}
          size="sm"
        />
      </div>

      <div className="pt-4 border-t border-[var(--color-border)]">
        <ConfidenceMeter confidence={confidence} size="sm" />
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
  const hasAnyData = PAIRS.some((p) => calls[p.label] || signals[p.label]);

  return (
    <section className="py-24 bg-[var(--color-elevated)]">
      <div className="max-w-[1152px] mx-auto px-6">
        <SectionHeader
          label="Live Snapshot"
          title="Today's regime calls"
          description="Published before the outcome is known. Validated after T+5 and T+20."
        />

        {!hasAnyData ? (
          <div className="border border-[var(--color-border)] bg-[var(--color-surface)] px-8 py-12 text-center">
            <p className="font-sans text-[13px] text-[var(--color-text-muted)]">
              Awaiting today&apos;s regime calls. The pipeline runs daily —
              check back soon.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {PAIRS.map((pair) => {
              const call = calls[pair.label];
              const signal = signals[pair.label];
              return (
                <Link
                  key={pair.label}
                  href={`/desk/fx-regime/${pair.label.toLowerCase()}`}
                >
                  <SnapshotCard
                    pair={pair.display}
                    pairColor={pair.pairColor}
                    spot={signal?.spot?.toFixed(4) ?? "—"}
                    regime={(call?.regime ?? "—").replace(/_/g, " ")}
                    regimeCategory={call?.regime ?? undefined}
                    confidence={call?.confidence ?? null}
                    date={call?.date ?? undefined}
                  />
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

/* ─── Validation Snapshot ───────────────────────────────────────────── */

function ValidationSnapshot({
  brierScore,
  winRate,
  sampleSize,
  totalCalls,
}: {
  brierScore: number | null;
  winRate: number | null;
  sampleSize: number | null;
  totalCalls: number;
}) {
  const brierLabel =
    brierScore == null
      ? "—"
      : brierScore < 0.1
        ? "Excellent calibration"
        : brierScore < 0.2
          ? "Good calibration"
          : brierScore < 0.3
            ? "Fair calibration"
            : "Poor calibration";

  return (
    <section className="py-24">
      <div className="max-w-[1152px] mx-auto px-6">
        <SectionHeader
          label="Validation"
          title="Every call validated. Append-only by convention."
          description="Directional accuracy is easy to game. Brier score measures calibration honesty — how well our confidence matches our accuracy."
        />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-px bg-[var(--color-border)] border border-[var(--color-border)] mb-10">
          <MetricCard
            label="Brier Score (Heuristic)"
            value={brierScore != null ? brierScore.toFixed(3) : "—"}
            sub={brierLabel}
            context={
              sampleSize != null
                ? `Based on ${sampleSize} published calls`
                : "Awaiting validation"
            }
            size="md"
            highlight={brierScore != null && brierScore < 0.25}
          />
          <MetricCard
            label="Win Rate (T+5)"
            value={winRate != null ? `${(winRate * 100).toFixed(1)}%` : "—"}
            sub="vs 50% random baseline"
            context={
              sampleSize != null && sampleSize < 200
                ? `n=${sampleSize} — statistical significance requires ~200 calls`
                : undefined
            }
            size="md"
          />
          <MetricCard
            label="Calls Published"
            value={totalCalls > 0 ? String(totalCalls) : "—"}
            sub="Since May 2026"
            size="md"
          />
          <MetricCard
            label="Pairs Tracked"
            value="3"
            sub="EUR/USD · USD/JPY · USD/INR"
            size="md"
          />
        </div>

        <div className="flex items-center justify-between flex-wrap gap-4 pt-6 border-t border-[var(--color-border)]">
          <p className="font-sans text-[13px] text-[var(--color-text-secondary)] max-w-[560px]">
            Outcomes measured against next-day spot with a 5bps dead-band. Our
            accuracy is currently near random — we publish this openly as part
            of our research process.{" "}
            <a href="/limitations" className="underline">
              See limitations
            </a>
            .
          </p>
          <Link
            href="/track-record"
            className="font-sans text-[13px] text-[var(--color-text-muted)] underline decoration-[var(--color-border)] underline-offset-4 transition-colors duration-300 hover:text-[var(--color-text)]"
          >
            Full track record →
          </Link>
        </div>
      </div>
    </section>
  );
}

/* ─── Signal Architecture ───────────────────────────────────────────── */

function SignalArchitecture() {
  const signals = [
    {
      n: "01",
      label: "Rate Differentials",
      desc: "2Y sovereign yield spreads. Primary driver of medium-term FX regime direction.",
      weight: "~45%",
    },
    {
      n: "02",
      label: "COT Positioning",
      desc: "CFTC weekly non-commercial net positions as percentile ranks. Crowd and reversal signals.",
      weight: "~25%",
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
      desc: "Open interest flows. Risk reversal data is pending (synthetic proxy removed in v2.1). INR-specific series included.",
      weight: "~5%",
    },
    {
      n: "05",
      label: "Special Factor",
      desc: "Pair-specific cross-asset signal — ECB sentiment for EUR/USD, JPY funding stress for USD/JPY, EM carry/RBI for USD/INR.",
      weight: "~5%",
    },
  ];

  return (
    <section className="py-24 bg-[var(--color-elevated)]">
      <div className="max-w-[1152px] mx-auto px-6">
        <SectionHeader
          label="Signal Architecture"
          title="Five signal families. One composite."
          description="Each family is scored against its own history, then weighted by pair-specific calibration. The composite drives the regime label."
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-[var(--color-border)] border border-[var(--color-border)]">
          {signals.map((s) => (
            <div
              key={s.n}
              className="bg-[var(--color-surface)] p-8 cursor-pointer glow-hover transition-all duration-500"
              style={
                {
                  "--glow-color": "rgba(231, 229, 228, 0.06)",
                } as React.CSSProperties
              }
            >
              <div className="flex items-start justify-between mb-6">
                <span className="font-sans text-[10px] tracking-[0.15em] text-[var(--color-text-muted)]">
                  {s.n}
                </span>
                <span className="font-sans text-[10px] tracking-[0.1em] text-[var(--color-text-muted)]">
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

/* ─── About Snippet ─────────────────────────────────────────────────── */

function AboutSnippet({
  siteContent,
}: {
  siteContent: Record<string, string>;
}) {
  const bio =
    siteContent["about.bio"] ??
    "Macro researcher focused on systematic FX regime classification.";
  const credentials =
    siteContent["about.credentials"] ??
    "EE Undergrad · Discretionary Macro Research";

  return (
    <section className="py-24">
      <div className="max-w-[1152px] mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-16 items-start">
          <div>
            <span className="block font-sans text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-4">
              About
            </span>
            <h3 className="font-sans font-semibold text-[22px] text-[var(--color-text)] tracking-tight leading-snug">
              Shreyash Sakhare
            </h3>
            <p className="font-sans text-[11px] text-[var(--color-brand-amber)] mt-2 tracking-wide">
              {credentials}
            </p>
          </div>

          <div>
            <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] max-w-[560px] mb-6">
              {bio}
            </p>
            <div className="flex gap-5">
              <Link
                href="/about"
                className="px-5 py-2 border border-[var(--color-border)] font-sans text-[13px] text-[var(--color-text-secondary)] transition-all duration-300 hover:bg-[var(--color-text)] hover:text-[var(--color-void)] hover:border-[var(--color-text)]"
                style={{ borderRadius: 2 }}
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

/* ─── Page ──────────────────────────────────────────────────────────── */

export default async function HomePage() {
  const supabase = await createClient();

  const [calls, signals, validation, statsT5, siteContent] = await Promise.all([
    getLatestRegimeCalls(supabase),
    getLatestSignals(supabase),
    getValidationLog(supabase),
    getValidationStats(supabase, "t5"),
    getSiteContent(supabase),
  ]);

  const { count } = await supabase
    .from("regime_calls")
    .select("*", { count: "exact", head: true })
    .gte("date", "2026-05-01");

  const correctCount = validation.filter((r) => r.outcome === "correct").length;
  const winRate =
    validation.length > 0 ? correctCount / validation.length : null;

  const allRow = statsT5.find((s) => s.pair === "ALL");
  const brierScore = allRow?.brierScore ?? null;
  const sampleSize = allRow?.sampleSize ?? null;

  const latestCallDate =
    Object.values(calls)
      .map((c) => c.date)
      .sort()
      .pop() ?? null;

  const schemaOrgDataset = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    name: "FX Regime Lab — Daily Regime Classifications",
    description:
      "Open-source research infrastructure for transparent macro regime monitoring. Every signal, every call, every mistake — published in real time.",
    url: "https://fxregimelab.com",
    creator: {
      "@type": "Person",
      name: "Shreyash Sakhare",
      url: "https://fxregimelab.com/about",
    },
    license: "https://creativecommons.org/licenses/by-nc/4.0/",
    variableMeasured: ["FX Regime", "Directional Accuracy", "Brier Score"],
    temporalCoverage: "2024/..",
    spatialCoverage: "Global FX Markets",
    distribution: {
      "@type": "DataDownload",
      contentUrl: "https://fxregimelab.com/track-record",
      encodingFormat: "HTML",
    },
  };

  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      <Script
        id="schema-dataset"
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schemaOrgDataset) }}
      />
      <Nav />
      <AuditTrailBannerServer variant="shell" />
      <main id="main-content">
        <HeroSection
          siteContent={siteContent}
          latestCallDate={latestCallDate}
        />
        <LiveSnapshot calls={calls} signals={signals} />
        <ValidationSnapshot
          brierScore={brierScore}
          winRate={winRate}
          sampleSize={sampleSize}
          totalCalls={count ?? 0}
        />
        <SignalArchitecture />
        <AboutSnippet siteContent={siteContent} />
        <ResearchDisclaimer />
      </main>
      <Footer />
    </div>
  );
}
