import { Footer } from "@/components/shell/Footer";
import { Nav } from "@/components/shell/Nav";
import { AuditTrailBannerServer } from "@/components/ui/audit-trail-banner";
import { ResearchDisclaimer } from "@/components/ui/research-disclaimer";
import { PAIRS } from "@/lib/constants";
import { getSiteContent, getValidationStats } from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";
import {
  Database,
  FileText,
  Globe,
  Link2,
  Mail,
  Scale,
  Shield,
} from "lucide-react";
import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { Suspense } from "react";

export const metadata: Metadata = {
  title: "About — FX Regime Lab",
  description:
    "Macro researcher building open-source FX regime monitoring infrastructure. Transparent signals, honest metrics, immutable ledgers.",
};

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="block font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-4">
      {children}
    </span>
  );
}

/* ─── Hero ──────────────────────────────────────────────────────────── */

function Hero() {
  return (
    <section className="reveal mb-20 pb-16 border-b border-[var(--color-border)]">
      <SectionLabel>About</SectionLabel>
      <h1 className="font-sans font-semibold text-[clamp(32px,4vw,52px)] text-[var(--color-text)] tracking-tight leading-[1.1] mb-6">
        About FX Regime Lab
      </h1>
      <p className="font-sans text-[17px] text-[var(--color-text-secondary)] leading-[1.7] max-w-[560px]">
        Open-source research infrastructure for transparent macro regime
        monitoring. Every signal, every call, every mistake — published in real
        time.
      </p>
    </section>
  );
}

/* ─── Philosophy ────────────────────────────────────────────────────── */

function Philosophy() {
  return (
    <section className="reveal mb-24">
      <SectionLabel>Philosophy</SectionLabel>
      <h2 className="font-sans font-semibold text-[24px] text-[var(--color-text)] tracking-tight leading-snug mb-6">
        Radical Honesty in Macro Research
      </h2>
      <div className="max-w-[640px] space-y-4">
        <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7]">
          Most macro research is narrative-driven, backtested to look good, and
          never validated in public. We are doing the opposite: building
          systematic tools, publishing every call before it resolves, and being
          brutally honest about our limitations.
        </p>
        <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7]">
          We currently do not have edge. Our accuracy is near random. But we are
          building the infrastructure — immutable ledgers, transparent
          validation, honest metrics — that will allow us to detect edge when we
          find it. And you will see the entire process in real time.
        </p>
        <div className="flex gap-5 pt-2">
          <Link
            href="/limitations"
            className="px-5 py-2 border border-[var(--color-border)] font-sans text-[13px] text-[var(--color-text-secondary)] transition-all duration-300 hover:bg-[var(--color-text)] hover:text-[var(--color-void)] hover:border-[var(--color-text)]"
            style={{ borderRadius: 2 }}
          >
            See our limitations
          </Link>
          <Link
            href="/journey"
            className="font-sans text-[13px] text-[var(--color-text-muted)] underline decoration-[var(--color-border)] underline-offset-4 transition-colors duration-300 hover:text-[var(--color-text)] py-2"
          >
            Our journey →
          </Link>
        </div>
      </div>
    </section>
  );
}

/* ─── Author Identity ───────────────────────────────────────────────── */

async function AuthorIdentity() {
  const supabase = await createClient();
  const siteContent = await getSiteContent(supabase, "about_bio");
  const bioText =
    siteContent.author_bio ??
    "Macro researcher focused on systematic FX regime classification. Built FX Regime Lab to bridge the gap between systematic FX regime monitoring and publicly accessible daily regime classifications.";

  return (
    <section className="reveal mb-24">
      <div className="grid grid-cols-1 md:grid-cols-[160px_1fr] gap-10 items-start">
        <div className="flex-shrink-0">
          <Image
            src="/profile/shreyash.png"
            alt="Shreyash Sakhare"
            width={140}
            height={140}
            className="rounded-full border border-[var(--color-border)] object-cover"
            priority
          />
        </div>

        {/* Bio */}
        <div>
          <h2 className="font-sans font-semibold text-[22px] text-[var(--color-text)] tracking-tight leading-snug mb-1">
            Shreyash Sakhare
          </h2>
          <p className="font-mono text-[11px] text-emerald-400 tracking-wide mb-5">
            Founder &amp; Lead Researcher
          </p>
          <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] max-w-[560px]">
            {bioText}
          </p>
        </div>
      </div>
    </section>
  );
}

/* ─── Methodology Summary ───────────────────────────────────────────── */

function MethodologySummary() {
  const bullets = [
    {
      label: "3-layer regime engine",
      desc: "Macro, technical, and micro-structure layers are scored independently and fused into a composite regime label.",
    },
    {
      label: "6 composite inputs",
      desc: "Rate differential, COT positioning, realized volatility, open interest, special factor, and FPI flow — weighted per pair.",
    },
    {
      label: "Out-of-sample validation",
      desc: "Every call is scored with Brier scores and directional accuracy. No ex-post fitting, no narrative revision.",
    },
    {
      label: "Immutable ledger",
      desc: "Every call is logged and validated in an append-only record. The database is the source of truth.",
    },
  ];

  return (
    <section className="reveal mb-24">
      <SectionLabel>Methodology</SectionLabel>
      <h2 className="font-sans font-semibold text-[24px] text-[var(--color-text)] tracking-tight leading-snug mb-8">
        How we classify regimes
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {bullets.map((b) => (
          <div
            key={b.label}
            className="bg-[var(--color-surface)] border border-[var(--color-border)] p-6"
          >
            <p className="font-sans font-semibold text-[14px] text-[var(--color-text)] mb-2">
              {b.label}
            </p>
            <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-[1.6]">
              {b.desc}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ─── Track Record Highlights ───────────────────────────────────────── */

async function TrackRecordHighlights() {
  const supabase = await createClient();
  const [{ count }, { data: datesData }, statsT5] = await Promise.all([
    supabase
      .from("validation_log")
      .select("*", { count: "exact", head: true }),
    supabase
      .from("validation_log")
      .select("date")
      .limit(1000),
    getValidationStats(supabase, "t5", "live"),
  ]);

  const distinctDates = new Set(
    (datesData as Array<{ date: string }> | null)?.map((d) => d.date) ?? [],
  );
  const daysCount = distinctDates.size;
  const allRow = statsT5.find((s) => s.pair === "ALL");
  const rolling90dAcc =
    allRow?.rolling90dAccuracy != null
      ? allRow.rolling90dAccuracy > 1
        ? allRow.rolling90dAccuracy / 100
        : allRow.rolling90dAccuracy
      : null;

  const stats = [
    {
      value: count ? count.toLocaleString() : "—",
      label: "Validated regime calls",
    },
    {
      value: String(PAIRS.length),
      label: "Currency pairs: EUR/USD, USD/JPY, USD/INR",
    },
    {
      value: daysCount > 0 ? daysCount.toLocaleString() : "—",
      label: "Trading days validated",
    },
    {
      value:
        rolling90dAcc != null ? `${(rolling90dAcc * 100).toFixed(1)}%` : "—",
      label: "Rolling 90-day accuracy",
    },
  ];

  return (
    <section className="reveal mb-24">
      <SectionLabel>Track Record</SectionLabel>
      <h2 className="font-sans font-semibold text-[24px] text-[var(--color-text)] tracking-tight leading-snug mb-8">
        Highlights
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-px bg-[var(--color-border)] border border-[var(--color-border)]">
        {stats.map((s) => (
          <div
            key={s.label}
            className="bg-[var(--color-surface)] p-6 md:p-8 cursor-pointer glow-hover transition-all duration-200"
            style={
              {
                "--glow-color": "rgba(52, 211, 153, 0.12)",
              } as React.CSSProperties
            }
          >
            <p className="font-mono text-[clamp(28px,4vw,40px)] font-medium text-emerald-400 tracking-tight leading-none mb-3 tabular-nums">
              {s.value}
            </p>
            <p className="font-mono text-[9px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase leading-relaxed">
              {s.label}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ─── Transparency Commitments ──────────────────────────────────────── */

function TransparencyCommitments() {
  const commitments = [
    {
      label: "Append-only validation",
      desc: "Every regime call is logged before the outcome is known. Validation rows are never mutated after write.",
    },
    {
      label: "Public methodology",
      desc: "Signal architecture, weighting, and regime thresholds are documented and versioned.",
    },
    {
      label: "No narrative revision",
      desc: "Post-hoc stories that fit the data are not added. The call either worked or it did not.",
    },
    {
      label: "Open benchmark",
      desc: "Regime-aware sizing is benchmarked against uniform exposure on the Track Record page.",
    },
  ];

  return (
    <section id="principles" className="reveal mb-24">
      <SectionLabel>Transparency</SectionLabel>
      <h2 className="font-sans font-semibold text-[24px] text-[var(--color-text)] tracking-tight leading-snug mb-8">
        Commitments
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {commitments.map((c) => (
          <div
            key={c.label}
            className="bg-[var(--color-surface)] border border-[var(--color-border)] p-6"
          >
            <p className="font-sans font-semibold text-[14px] text-[var(--color-text)] mb-2">
              {c.label}
            </p>
            <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-[1.6]">
              {c.desc}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ─── Data Sources ──────────────────────────────────────────────────── */

function DataSources() {
  const sources = [
    {
      icon: Database,
      name: "FRED API",
      description:
        "Federal Reserve Economic Data — rate differentials, inflation expectations, and macroeconomic indicators.",
      url: "https://fred.stlouisfed.org/",
    },
    {
      icon: Database,
      name: "Yahoo Finance",
      description:
        "Spot FX prices, realized volatility calculations, and historical price data for regime validation.",
      url: "https://finance.yahoo.com/",
    },
    {
      icon: FileText,
      name: "CFTC COT Reports",
      description:
        "Commitment of Traders positioning data for institutional positioning analysis.",
      url: "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm",
    },
    {
      icon: Globe,
      name: "Investing.com Economic Calendar",
      description:
        "Scheduled macro events, central bank meetings, and high-impact event tracking.",
      url: "https://www.investing.com/economic-calendar/",
    },
  ];

  return (
    <section className="reveal mb-24">
      <SectionLabel>Data Sources</SectionLabel>
      <h2 className="font-sans font-semibold text-[24px] text-[var(--color-text)] tracking-tight leading-snug mb-8">
        Where the data comes from
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sources.map((s) => (
          <a
            key={s.name}
            href={s.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-start gap-4 bg-[var(--color-surface)] border border-[var(--color-border)] p-5 hover:border-[var(--color-border-bright)] transition-all duration-300"
          >
            <div className="mt-0.5 p-2 bg-[var(--color-void)] border border-[var(--color-border)]">
              <s.icon className="w-4 h-4 text-[var(--color-text-muted)] group-hover:text-[var(--color-text)] transition-colors" />
            </div>
            <div>
              <p className="font-sans font-semibold text-[14px] text-[var(--color-text)] mb-1">
                {s.name}
              </p>
              <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-[1.6]">
                {s.description}
              </p>
            </div>
          </a>
        ))}
      </div>
    </section>
  );
}

/* ─── Legal ─────────────────────────────────────────────────────────── */

function Legal() {
  return (
    <section className="reveal mb-24">
      <SectionLabel>Legal</SectionLabel>
      <h2 className="font-sans font-semibold text-[24px] text-[var(--color-text)] tracking-tight leading-snug mb-8">
        Disclaimers &amp; Terms
      </h2>
      <div className="space-y-4">
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-6">
          <div className="flex items-center gap-3 mb-3">
            <Shield className="w-4 h-4 text-[var(--color-brand-amber)]" />
            <h3 className="font-sans font-semibold text-[14px] text-[var(--color-text)]">
              Not Investment Advice
            </h3>
          </div>
          <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-[1.7]">
            FX Regime Lab is a research publication, not a financial advisor.
            All content — regime classifications, signal scores, and briefs — is
            provided for informational and educational purposes only. Nothing
            herein constitutes investment advice, a solicitation to buy or sell
            any security, or a recommendation of any trading strategy. Past
            performance does not guarantee future results.
          </p>
        </div>
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-6">
          <div className="flex items-center gap-3 mb-3">
            <Scale className="w-4 h-4 text-[var(--color-brand-amber)]" />
            <h3 className="font-sans font-semibold text-[14px] text-[var(--color-text)]">
              Data Accuracy &amp; Limitations
            </h3>
          </div>
          <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-[1.7]">
            We source data from public APIs (FRED, Yahoo Finance, CFTC) and make
            every effort to ensure accuracy. However, data may be delayed,
            incorrect, or incomplete. FX Regime Lab assumes no liability for
            decisions made based on this data. Users should verify any data
            point with primary sources before acting on it.
          </p>
        </div>
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-6">
          <div className="flex items-center gap-3 mb-3">
            <FileText className="w-4 h-4 text-[var(--color-brand-amber)]" />
            <h3 className="font-sans font-semibold text-[14px] text-[var(--color-text)]">
              Intellectual Property
            </h3>
          </div>
          <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-[1.7]">
            All content, methodology, signal architectures, and code are the
            intellectual property of FX Regime Lab. Unauthorized reproduction,
            redistribution, or commercial use without written permission is
            prohibited.
          </p>
        </div>
      </div>
    </section>
  );
}

/* ─── V2 Release Notes ──────────────────────────────────────────────── */

function V2ReleaseNotes() {
  const notes = [
    {
      date: "June 2026 — V3 Redesign",
      items: [
        "Complete UX/UI redesign: principle-first, Brier-first metrics",
        "Information architecture restructure (Research, Desk, Validation, About)",
        "Cross-Asset Matrix: data-empty tiles hidden, only real data shown",
        "Sample size context on Track Record page",
        "About page expansion: Data Sources, Legal, editable bio",
        "CMS via site_content table for editable copy",
        "Feature flag system for progressive rollout",
      ],
    },
    {
      date: "May 2026",
      items: [
        "Regime Validation panel added to Track Record",
        "T+20 validation live for all three pairs",
        "MAD Z-score normalization for rate signals",
        "Platt calibration for confidence scores",
        "Per-pair macro tiles in Cross-Asset Matrix",
      ],
    },
    {
      date: "April 2026",
      items: [
        "V1 launch with EUR/USD, USD/JPY, USD/INR",
        "T+5 directional validation",
        "Daily brief automation",
        "Signal inspector drawer",
      ],
    },
  ];

  return (
    <section className="reveal mb-24">
      <SectionLabel>Release Notes</SectionLabel>
      <h2 className="font-sans font-semibold text-[24px] text-[var(--color-text)] tracking-tight leading-snug mb-8">
        Version History
      </h2>
      <div className="flex flex-col gap-6">
        {notes.map((n) => (
          <div
            key={n.date}
            className="bg-[var(--color-surface)] border border-[var(--color-border)] p-6"
          >
            <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-4">
              {n.date}
            </p>
            <ul className="flex flex-col gap-2">
              {n.items.map((item) => (
                <li
                  key={item}
                  className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-[1.6] flex items-start gap-2"
                >
                  <span className="text-[var(--color-text-muted)] mt-1.5">
                    ·
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ─── Contact / Connect ─────────────────────────────────────────────── */

function ContactConnect() {
  const links = [
    {
      icon: Mail,
      label: "Email",
      href: "mailto:shreyash@fxregimelab.com",
      display: "shreyash@fxregimelab.com",
    },
    {
      icon: Link2,
      label: "GitHub",
      href: "https://github.com/fxregimelab",
      display: "github.com/fxregimelab",
    },
  ];

  return (
    <section id="contact" className="reveal mb-24">
      <SectionLabel>Contact</SectionLabel>
      <h2 className="font-sans font-semibold text-[24px] text-[var(--color-text)] tracking-tight leading-snug mb-8">
        Connect
      </h2>
      <div className="flex flex-col gap-3 max-w-[480px]">
        {links.map((l) => (
          <Link
            key={l.label}
            href={l.href}
            className="group flex items-center gap-4 px-5 py-3.5 border border-[var(--color-border)] bg-[var(--color-surface)] cursor-pointer transition-all duration-300 hover:bg-[var(--color-elevated)] hover:border-[var(--color-border-bright)] glow-hover"
          >
            <l.icon className="w-4 h-4 text-[var(--color-text-muted)] group-hover:text-[var(--color-text)] transition-colors duration-300" />
            <div>
              <p className="font-sans text-[13px] text-[var(--color-text)] font-medium">
                {l.label}
              </p>
              <p className="font-mono text-[11px] text-[var(--color-text-muted)] group-hover:text-[var(--color-text-secondary)] transition-colors duration-300">
                {l.display}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}

/* ─── Disclaimer ────────────────────────────────────────────────────── */

function Disclaimer() {
  return (
    <section className="reveal mb-10">
      <p className="font-mono text-[10px] text-[var(--color-text-muted)] leading-relaxed max-w-[640px]">
        FX Regime Lab is a research publication, not investment advice. Past
        performance does not guarantee future results.
      </p>
    </section>
  );
}

/* ─── Page ──────────────────────────────────────────────────────────── */

export default async function AboutPage() {
  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      <Nav />
      <AuditTrailBannerServer variant="shell" />
      <main
        id="main-content"
        className="max-w-4xl mx-auto px-6 pt-28 pb-20 w-full"
      >
        <Hero />
        <Philosophy />
        <Suspense fallback={<div className="animate-pulse h-40 bg-[var(--color-surface)] rounded mb-8" />}>
          <AuthorIdentity />
        </Suspense>
        <MethodologySummary />
        <Suspense fallback={<div className="animate-pulse h-40 bg-[var(--color-surface)] rounded mb-8" />}>
          <TrackRecordHighlights />
        </Suspense>
        <TransparencyCommitments />
        <DataSources />
        <Legal />
        <V2ReleaseNotes />
        <ContactConnect />
        <ResearchDisclaimer />
      </main>
      <Footer />
    </div>
  );
}
