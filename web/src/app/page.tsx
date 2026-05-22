import { Footer } from "@/components/shell/Footer";
import { Nav } from "@/components/shell/Nav";
import { AuditTrailBannerServer } from "@/components/ui/audit-trail-banner";
import { ResearchDisclaimer } from "@/components/ui/research-disclaimer";
import { normalizeProp } from "@/components/ui/utils";
import { PAIRS } from "@/lib/constants";
import {
  type ValidationRow,
  getLatestRegimeCalls,
  getLatestSignals,
  getValidationLog,
  getValidationStats,
} from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";
import type { Metadata } from "next";
import Link from "next/link";
import Script from "next/script";

export const metadata: Metadata = {
  title: "FX Regime Lab — Daily Regime Calls",
  description:
    "Daily macro regime classifications for EUR/USD, USD/JPY, and USD/INR. On the record.",
};

/* ─── Section primitives ────────────────────────────────────────────── */

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="block font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-4">
      {children}
    </span>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="font-sans font-semibold text-[28px] text-[var(--color-text)] tracking-tight leading-snug">
      {children}
    </h2>
  );
}

/* ─── Hero ──────────────────────────────────────────────────────────── */

function Hero({
  latestCallDate,
  totalCalls,
  accuracy7d,
  accuracy90d,
  last7Length,
}: {
  latestCallDate: string | null;
  totalCalls: number;
  accuracy7d: number;
  accuracy90d: number | null;
  last7Length: number;
}) {
  return (
    <section className="min-h-[100dvh] flex flex-col justify-between relative">
      <div className="max-w-[1152px] mx-auto px-6 w-full pt-28">
        {/* Brand mark + rule */}
        <div className="mb-10 animate-fade-in">
          <span className="font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase block mb-4">
            FX Regime Lab
          </span>
          <div className="w-[96px] h-px bg-[var(--color-border)] animate-line-grow" />
        </div>

        {/* H1 */}
        <h1 className="font-sans font-semibold text-[clamp(40px,5vw,68px)] text-[var(--color-text)] leading-[1.08] tracking-tight mb-8 max-w-[640px] animate-fade-up delay-100">
          FX Regime Classification System. V2.
        </h1>

        {/* Manifesto paragraph */}
        <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] max-w-[480px] mb-10 animate-fade-up delay-200">
          Published daily. Validated out-of-sample at T+5 and T+20. Regime-aware
          sizing benchmark against uniform exposure. Three pairs, six composite
          inputs, one track record. The record is open.
        </p>

        {/* System status strip */}
        <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2 mb-10 animate-fade-up delay-300">
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-[11px] tracking-[0.12em] text-[var(--color-text-muted)] uppercase">
              Latest call
            </span>
            <span className="font-mono text-[11px] text-[var(--color-text)] tabular-nums">
              {latestCallDate ?? "—"}
            </span>
          </div>
          <span className="text-[var(--color-border)]">·</span>
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-[11px] tracking-[0.12em] text-[var(--color-text-muted)] uppercase">
              Pairs tracked
            </span>
            <span className="font-mono text-[11px] text-[var(--color-text)] tabular-nums">
              {PAIRS.length}
            </span>
          </div>
          <span className="text-[var(--color-border)]">·</span>
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-[11px] tracking-[0.12em] text-[var(--color-text-muted)] uppercase">
              Model version
            </span>
            <span className="font-mono text-[11px] text-[var(--color-text)] tabular-nums">
              v2
            </span>
          </div>
          <span className="text-[var(--color-border)]">·</span>
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-[11px] tracking-[0.12em] text-[var(--color-text-muted)] uppercase">
              Calls since May 2026
            </span>
            <span className="font-mono text-[11px] text-[var(--color-text)] tabular-nums">
              {totalCalls > 0 ? totalCalls : "—"}
            </span>
          </div>
          <span className="text-[var(--color-border)]">·</span>
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-[11px] tracking-[0.12em] text-[var(--color-text-muted)] uppercase">
              7D Calibration
            </span>
            <span className="font-mono text-[11px] text-[var(--color-text)] tabular-nums">
              {last7Length > 0 ? `${accuracy7d.toFixed(1)}%` : "—"}
            </span>
          </div>
          <span className="text-[var(--color-border)]">·</span>
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-[11px] tracking-[0.12em] text-[var(--color-text-muted)] uppercase">
              90D Accuracy
            </span>
            <span className="font-mono text-[11px] text-[var(--color-text)] tabular-nums">
              {accuracy90d != null
                ? `${((normalizeProp(accuracy90d) ?? 0) * 100).toFixed(1)}%`
                : "—"}
            </span>
          </div>
        </div>

        {/* Single CTA */}
        <div className="animate-fade-up delay-400">
          <Link
            href="/terminal"
            className="inline-block px-7 py-3.5 bg-[var(--color-text)] text-[var(--color-void)] font-sans text-[14px] font-medium tracking-[0.02em] cursor-pointer glow-hover transition-all duration-200 hover:bg-[var(--color-accent)]"
            style={
              {
                "--glow-color": "rgba(231, 229, 228, 0.15)",
              } as React.CSSProperties
            }
          >
            Open the terminal
          </Link>
        </div>
      </div>

      {/* Scroll hint */}
      <div className="max-w-[1152px] mx-auto px-6 w-full pb-10">
        <div className="flex justify-center animate-fade-in delay-700">
          <span className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
            Scroll
          </span>
        </div>
      </div>
    </section>
  );
}

/* ─── Validation Ticker ─────────────────────────────────────────────── */

const PAIR_COLOR: Record<string, string> = Object.fromEntries(
  PAIRS.flatMap((p) => [
    [p.label, p.pairColor],
    [p.display, p.pairColor],
  ]),
);

function ValidationTicker({ rows }: { rows: ValidationRow[] }) {
  const recent = rows.slice(0, 16);
  if (recent.length === 0) return null;

  const items = recent.map((r) => {
    const pairKey = r.pair.replace(/\//g, "");
    const pairDisplay = PAIR_DISPLAY[r.pair] ?? r.pair;
    const color =
      PAIR_COLOR[pairKey] ??
      PAIR_COLOR[r.pair] ??
      "var(--color-text-secondary)";
    const sign = r.return_pct >= 0 ? "+" : "";
    return {
      date: r.date,
      pair: pairDisplay,
      pairColor: color,
      regime: r.call,
      outcome: r.outcome,
      outcomeLabel:
        r.outcome === "correct"
          ? "✓ CORRECT"
          : r.outcome === "neutral"
            ? "○ NEUTRAL"
            : "✗ INCORRECT",
      returnPct: `${sign}${r.return_pct.toFixed(2)}%`,
      returnPositive: r.return_pct >= 0,
    };
  });

  const Item = ({
    item,
  }: {
    item: (typeof items)[number];
  }) => (
    <div className="inline-flex items-center gap-4 px-6 shrink-0">
      <span className="font-mono text-[11px] tabular-nums text-[var(--color-text-muted)]">
        {item.date}
      </span>
      <span
        className="font-mono text-[11px] font-medium tracking-wide uppercase"
        style={{ color: item.pairColor }}
      >
        {item.pair}
      </span>
      <span className="font-mono text-[11px] text-[var(--color-text-secondary)] tracking-wide max-w-[180px] truncate">
        {item.regime.replace(/_/g, " ")}
      </span>
      <span
        className="font-mono text-[11px] font-medium tracking-wide uppercase"
        style={{
          color:
            item.outcome === "correct"
              ? "var(--color-up)"
              : item.outcome === "neutral"
                ? "var(--color-text-muted)"
                : "var(--color-down)",
        }}
      >
        {item.outcomeLabel}
      </span>
      <span
        className="font-mono text-[11px] font-medium tabular-nums"
        style={{
          color: item.returnPositive ? "var(--color-up)" : "var(--color-down)",
        }}
      >
        {item.returnPct}
      </span>
    </div>
  );

  return (
    <div className="border-y border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden h-[48px] flex items-center">
      <div className="flex animate-ticker-marquee hover:[animation-play-state:paused]">
        {items.map((item) => (
          <div
            key={`a-${item.date}-${item.pair}`}
            className="inline-flex items-center"
          >
            <Item item={item} />
            <span className="text-[var(--color-border)] font-mono text-[11px] px-2">
              ◆
            </span>
          </div>
        ))}
        {items.map((item) => (
          <div
            key={`b-${item.date}-${item.pair}`}
            className="inline-flex items-center"
          >
            <Item item={item} />
            <span className="text-[var(--color-border)] font-mono text-[11px] px-2">
              ◆
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

const PAIR_DISPLAY: Record<string, string> = Object.fromEntries(
  PAIRS.map((p) => [p.label, p.display]),
);

/* ─── Live snapshot cards ───────────────────────────────────────────── */

function SnapshotCard({
  pair,
  pairColor,
  spot,
  regime,
  confidence,
  date,
  delay,
}: {
  pair: string;
  pairColor: string;
  spot: string;
  regime: string;
  confidence: number | null;
  date?: string;
  delay: number;
}) {
  return (
    <div
      className="reveal border border-[var(--color-border)] bg-[var(--color-surface)] p-8 hover-lift cursor-pointer glow-hover transition-all duration-500"
      style={
        {
          transitionDelay: `${delay}ms`,
          "--glow-color": `${pairColor}22`,
        } as React.CSSProperties
      }
    >
      {/* Pair-colored top border */}
      <div
        className="absolute top-0 left-0 right-0 h-[1px]"
        style={{ backgroundColor: pairColor }}
      />
      <div className="flex items-baseline justify-between mb-6">
        <span
          className="font-mono text-[11px] tracking-[0.15em] uppercase font-medium"
          style={{ color: pairColor }}
        >
          {pair}
        </span>
        <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
          {date ? date : "Spot"}
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
            {confidence != null
              ? `${Math.min(
                  100,
                  Math.max(
                    0,
                    Math.round((normalizeProp(confidence) ?? 0) * 100),
                  ),
                )}%`
              : "—"}
          </span>
        </div>
        <div className="h-[3px] bg-[var(--color-border)] overflow-hidden">
          <div
            className={`h-full transition-all duration-1000 ease-out ${confidence != null ? "bg-[var(--color-accent)]" : "bg-[var(--color-text-dim)]"}`}
            style={{
              width:
                confidence != null
                  ? `${Math.min(100, Math.max(0, (normalizeProp(confidence) ?? 0) * 100))}%`
                  : "0%",
            }}
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
  const hasAnyData = PAIRS.some((p) => calls[p.label] || signals[p.label]);

  return (
    <section className="py-28">
      <div className="max-w-[1152px] mx-auto px-6">
        <div className="reveal mb-14">
          <SectionLabel>Live Snapshot</SectionLabel>
          <div className="flex items-end justify-between flex-wrap gap-4">
            <SectionTitle>Latest regime calls</SectionTitle>
            <Link
              href="/terminal"
              className="font-sans text-[13px] text-[var(--color-text-muted)] underline decoration-[var(--color-border)] underline-offset-4 transition-colors duration-300 hover:text-[var(--color-text)]"
            >
              Open full terminal →
            </Link>
          </div>
        </div>

        {!hasAnyData ? (
          <div className="reveal border border-[var(--color-border)] bg-[var(--color-surface)] px-8 py-12">
            <p className="font-mono text-[11px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-2">
              Awaiting data
            </p>
            <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] max-w-[480px]">
              No regime calls logged yet. The pipeline runs daily — check back
              soon.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {PAIRS.map((pair, i) => {
              const call = calls[pair.label];
              const signal = signals[pair.label];
              return (
                <SnapshotCard
                  key={pair.label}
                  pair={pair.display}
                  pairColor={pair.pairColor}
                  spot={signal?.spot?.toFixed(4) ?? "—"}
                  regime={(call?.regime ?? "—").replace(/_/g, " ")}
                  confidence={call?.confidence ?? null}
                  date={call?.date ?? undefined}
                  delay={(i + 1) * 100}
                />
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

/* ─── Manifesto ─────────────────────────────────────────────────────── */

function Manifesto() {
  return (
    <section className="py-28 bg-[var(--color-elevated)]">
      <div className="max-w-[1152px] mx-auto px-6">
        <div className="reveal max-w-[720px]">
          <SectionLabel>Principle</SectionLabel>
          <blockquote
            className="font-serif font-light text-[clamp(24px,3.5vw,40px)] text-[var(--color-text)] leading-[1.3] tracking-tight"
            style={{
              fontFamily: "var(--font-playfair), ui-serif, Georgia, serif",
            }}
          >
            Credibility compounds through calendar discipline and honest
            validation, not marketing.
          </blockquote>
          <p className="font-sans text-[13px] text-[var(--color-text-muted)] mt-8 leading-relaxed max-w-[480px]">
            Any discretionary framework can be constructed to look correct in
            hindsight. The only meaningful test is publishing the call before
            the outcome is known — and logging the result without revision.
          </p>
        </div>
      </div>
    </section>
  );
}

/* ─── Signal architecture ───────────────────────────────────────────── */

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
      desc: "Open interest flows and 25-delta risk reversals. INR-specific series included.",
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
    <section className="py-28">
      <div className="max-w-[1152px] mx-auto px-6">
        <div className="reveal mb-14">
          <SectionLabel>Signal Architecture</SectionLabel>
          <SectionTitle>
            Five signal families.
            <br />
            One composite.
          </SectionTitle>
          <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] max-w-[480px] mt-4">
            Each family is scored against its own history, then weighted by
            pair-specific calibration. The composite drives the regime label.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-[var(--color-border)] border border-[var(--color-border)]">
          {signals.map((s, i) => (
            <div
              key={s.n}
              className="reveal bg-[var(--color-surface)] p-8 cursor-pointer glow-hover transition-all duration-500"
              style={
                {
                  transitionDelay: `${(i + 1) * 100}ms`,
                  "--glow-color": "rgba(231, 229, 228, 0.06)",
                } as React.CSSProperties
              }
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

/* ─── V2 Release Highlights ─────────────────────────────────────────── */

function V2Highlights() {
  const highlights = [
    {
      label: "Regime Validation",
      desc: "Regime-aware sizing benchmarked against uniform exposure on the Track Record page.",
    },
    {
      label: "T+20 Validation",
      desc: "Directional accuracy now measured at both T+5 and T+20 horizons.",
    },
    {
      label: "MAD Z-Scores",
      desc: "Rate signal normalization switched from Gaussian to median-absolute-deviation for tail robustness.",
    },
    {
      label: "Platt Calibration",
      desc: "Confidence scores calibrated with Platt scaling to reduce overconfidence bias.",
    },
  ];

  return (
    <section className="py-28 bg-[var(--color-elevated)]">
      <div className="max-w-[1152px] mx-auto px-6">
        <div className="reveal mb-14">
          <span className="block font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-4">
            V2 Release
          </span>
          <h2 className="font-sans font-semibold text-[28px] text-[var(--color-text)] tracking-tight leading-snug">
            What changed in V2
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-[var(--color-border)] border border-[var(--color-border)]">
          {highlights.map((h, i) => (
            <div
              key={h.label}
              className="reveal bg-[var(--color-surface)] p-8 cursor-pointer glow-hover transition-all duration-500"
              style={
                {
                  transitionDelay: `${(i + 1) * 100}ms`,
                  "--glow-color": "rgba(231, 229, 228, 0.06)",
                } as React.CSSProperties
              }
            >
              <h3 className="font-sans font-semibold text-[15px] text-[var(--color-text)] mb-2">
                {h.label}
              </h3>
              <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-[1.6]">
                {h.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── Validation trust ──────────────────────────────────────────────── */

function ValidationTrust({
  accuracy,
  accuracy7d,
  totalCalls,
  last7Length,
}: {
  accuracy: number;
  accuracy7d: number;
  totalCalls: number;
  last7Length: number;
}) {
  const stats = [
    { label: "Pairs tracked", value: String(PAIRS.length) },
    {
      label: "Calls since May 2026",
      value: totalCalls > 0 ? String(totalCalls) : "—",
    },
    {
      label: "All-time accuracy",
      value: totalCalls > 0 ? `${accuracy.toFixed(1)}%` : "—",
    },
    {
      label: "7D accuracy",
      value: last7Length > 0 ? `${accuracy7d.toFixed(1)}%` : "—",
    },
  ];

  return (
    <section className="py-28 bg-[var(--color-elevated)]">
      <div className="max-w-[1152px] mx-auto px-6">
        <div className="reveal mb-14">
          <SectionLabel>Validation</SectionLabel>
          <SectionTitle>
            Every call validated. Append-only by convention.
          </SectionTitle>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[var(--color-border)] border border-[var(--color-border)] mb-12">
          {stats.map((s, i) => (
            <div
              key={s.label}
              className="reveal bg-[var(--color-surface)] py-10 px-8 cursor-pointer glow-hover transition-all duration-500"
              style={
                {
                  transitionDelay: `${(i + 1) * 100}ms`,
                  "--glow-color": "rgba(231, 229, 228, 0.06)",
                } as React.CSSProperties
              }
            >
              <p className="font-mono text-[clamp(36px,5vw,56px)] font-medium text-[var(--color-text)] tracking-tight leading-none mb-3 tabular-nums">
                {s.value}
              </p>
              <p className="font-mono text-[9px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase">
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
            href="/methodology"
            className="font-sans text-[13px] text-[var(--color-text-muted)] underline decoration-[var(--color-border)] underline-offset-4 transition-colors duration-300 hover:text-[var(--color-text)]"
          >
            View methodology →
          </Link>
        </div>
      </div>
    </section>
  );
}

/* ─── About snippet ─────────────────────────────────────────────────── */

function AboutSnippet() {
  return (
    <section className="py-28">
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
              Studying how major FX regimes form and break using rate
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

/* ─── Page ──────────────────────────────────────────────────────────── */

export default async function HomePage() {
  const supabase = await createClient();

  const [calls, signals, validation, statsT5] = await Promise.all([
    getLatestRegimeCalls(supabase),
    getLatestSignals(supabase),
    getValidationLog(supabase),
    getValidationStats(supabase, "t5"),
  ]);

  const { count } = await supabase
    .from("regime_calls")
    .select("*", { count: "exact", head: true })
    .gte("date", "2026-05-01");

  const correctCount = validation.filter((r) => r.outcome === "correct").length;
  const accuracy =
    validation.length > 0 ? (correctCount / validation.length) * 100 : 0;

  // 7D accuracy
  const cut7 = new Date();
  cut7.setUTCDate(cut7.getUTCDate() - 7);
  const cut7Str = cut7.toISOString().slice(0, 10);
  const last7 = validation.filter((r) => r.date >= cut7Str);
  const correct7 = last7.filter((r) => r.outcome === "correct").length;
  const accuracy7d = last7.length > 0 ? (correct7 / last7.length) * 100 : 0;

  // Latest call date from calls
  const latestCallDate =
    Object.values(calls)
      .map((c) => c.date)
      .sort()
      .pop() ?? null;

  const accuracy90d =
    statsT5.length > 0 && !statsT5.every((s) => s.rolling90dAccuracy == null)
      ? statsT5.reduce((sum, s) => sum + (s.rolling90dAccuracy ?? 0), 0) /
        statsT5.length
      : null;

  const schemaOrgDataset = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    name: "FX Regime Lab — Daily Regime Classifications",
    description:
      "Published daily regime classifications for EUR/USD, USD/JPY, and USD/INR. Validated out-of-sample with Brier scores and directional accuracy.",
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
        <Hero
          latestCallDate={latestCallDate}
          totalCalls={count ?? 0}
          accuracy7d={accuracy7d}
          accuracy90d={accuracy90d}
          last7Length={last7.length}
        />
        <ValidationTicker rows={validation} />
        <LiveSnapshot calls={calls} signals={signals} />
        <Manifesto />
        <SignalArchitecture />
        <V2Highlights />
        <ValidationTrust
          accuracy={accuracy}
          accuracy7d={accuracy7d}
          totalCalls={count ?? 0}
          last7Length={last7.length}
        />
        <AboutSnippet />
        <ResearchDisclaimer />
      </main>
      <Footer />
    </div>
  );
}
