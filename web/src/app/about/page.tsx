import { Footer } from "@/components/shell/Footer";
import { Nav } from "@/components/shell/Nav";
import { AuditTrailBannerServer } from "@/components/ui/audit-trail-banner";
import { ResearchDisclaimer } from "@/components/ui/research-disclaimer";
import { getValidationStats } from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";
import { Link2, Mail, MessageCircle } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "About — FX Regime Lab",
  description: "What FX Regime Lab is, what it is not, and how it works.",
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
        Systematic FX macro research, published daily.
      </p>
    </section>
  );
}

/* ─── Author Identity ───────────────────────────────────────────────── */

function AuthorIdentity() {
  return (
    <section className="reveal mb-24">
      <div className="grid grid-cols-1 md:grid-cols-[160px_1fr] gap-10 items-start">
        {/* Profile placeholder */}
        <div className="flex-shrink-0">
          <div className="w-[120px] h-[120px] md:w-[140px] md:h-[140px] rounded-full bg-[var(--color-surface)] border border-[var(--color-border)] flex items-center justify-center">
            <span className="font-sans font-semibold text-[32px] text-[var(--color-text-muted)]">
              SS
            </span>
          </div>
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
            Macro researcher focused on systematic FX regime classification.
            Built FX Regime Lab to bridge the gap between institutional-grade
            quantitative research and publicly accessible daily regime
            classifications.
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
  const { count } = await supabase
    .from("validation_log")
    .select("*", { count: "exact", head: true });

  const { data: datesData } = await supabase
    .from("validation_log")
    .select("date")
    .limit(1000);
  const distinctDates = new Set(
    (datesData as Array<{ date: string }> | null)?.map((d) => d.date) ?? [],
  );
  const daysCount = distinctDates.size;

  const statsT5 = await getValidationStats(supabase, "t5", "live");
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
      value: "3",
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
    <section className="reveal mb-24">
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

/* ─── V2 Release Notes ──────────────────────────────────────────────── */

function V2ReleaseNotes() {
  const notes = [
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
      href: "mailto:desk@fxregimelab.com",
      display: "desk@fxregimelab.com",
    },
    {
      icon: Link2,
      label: "GitHub",
      href: "https://github.com/fxregimelab",
      display: "github.com/fxregimelab",
    },
  ];

  return (
    <section className="reveal mb-24">
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
        <AuthorIdentity />
        <MethodologySummary />
        <TrackRecordHighlights />
        <TransparencyCommitments />
        <V2ReleaseNotes />
        <ContactConnect />
        <Disclaimer />
        <ResearchDisclaimer />
      </main>
      <Footer />
    </div>
  );
}
