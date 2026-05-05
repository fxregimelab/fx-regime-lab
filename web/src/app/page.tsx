import Link from "next/link";
import { Nav } from "@/components/shell/Nav";
import { Footer } from "@/components/shell/Footer";
import { HeroRegimeCard } from "@/components/regime/HeroRegimeCard";
import { PairCard } from "@/components/regime/PairCard";
import { ValidationTable } from "@/components/regime/ValidationTable";
import { RegimeHeatmap } from "@/components/regime/RegimeHeatmap";
import { createClient } from "@/lib/supabase/server";
import {
  getLatestRegimeCalls,
  getLatestSignals,
  getValidationLog,
} from "@/lib/supabase/queries";
import { PAIRS } from "@/lib/constants";
import type { LatestRegimeCall, LatestSignal, ValidationRow } from "@/lib/supabase/queries";

export default async function HomePage() {
  const supabase = await createClient();

  const [calls, signals, validation] = await Promise.all([
    getLatestRegimeCalls(supabase),
    getLatestSignals(supabase),
    getValidationLog(supabase, 6),
  ]);

  const eurCall = calls["EURUSD"] as LatestRegimeCall | undefined;
  const eurSig = signals["EURUSD"] as LatestSignal | undefined;

  const correctCount = validation.filter(
    (r: ValidationRow) => r.outcome === "correct"
  ).length;
  const accuracy =
    validation.length > 0
      ? ((correctCount / validation.length) * 100).toFixed(1)
      : "0.0";

  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="min-h-screen flex flex-col bg-white">
      <Nav />
      <main className="flex-1">
        {/* Hero */}
        <section className="max-w-[1152px] mx-auto px-6 py-[72px] pb-16 grid grid-cols-1 md:grid-cols-2 gap-16 items-start">
          <div>
            <div className="flex items-center gap-2.5 mb-7">
              <div className="w-1.5 h-1.5 rounded-full bg-up flex-shrink-0" />
              <span className="font-mono text-[11px] text-shell-secondary tracking-[0.1em]">
                LIVE · G10 FX · DAILY CALLS
              </span>
            </div>
            <h1 className="font-sans font-extrabold text-[52px] leading-[1.05] text-shell-text tracking-tight mb-6">
              Daily regime
              <br />
              calls. On the
              <br />
              record.
            </h1>
            <p className="font-sans text-base text-shell-secondary leading-relaxed max-w-[440px] mb-8">
              G10 FX regime classification across EUR/USD, USD/JPY, and USD/INR.
              Composite signal from rate differentials, COT positioning, realized
              volatility, and open interest. Every call public before market open.
              Every outcome validated.
            </p>
            <div className="flex gap-3 flex-wrap items-center">
              <Link
                href="/brief"
                className="bg-shell-text text-white font-sans font-semibold text-[13px] px-5 py-2.5"
              >
                Read today&apos;s brief
              </Link>
              <Link
                href="/performance"
                className="font-sans font-medium text-[13px] text-shell-text underline decoration-[#d0d0d0] underline-offset-4"
              >
                Validation log →
              </Link>
            </div>
            <div className="mt-9 flex items-center gap-2 pt-6 border-t border-[#f0f0f0]">
              <span className="w-[5px] h-[5px] rounded-full bg-up flex-shrink-0" />
              <span className="font-mono text-[10px] text-shell-muted tracking-wider">
                PIPELINE · {today} · 3 pairs updated
              </span>
            </div>
          </div>
          <div>
            <HeroRegimeCard call={eurCall ?? null} signals={eurSig ?? null} />
          </div>
        </section>

        <div className="border-t border-shell-border" />

        {/* Stats bar */}
        <section className="border-b border-shell-border">
          <div className="max-w-[1152px] mx-auto px-6 grid grid-cols-2 md:grid-cols-4">
            {[
              { label: "Pairs tracked", value: "3" },
              { label: "Calls since April 2026", value: "27" },
              { label: "7-day accuracy", value: `${accuracy}%` },
              { label: "Signal families", value: "4" },
            ].map((s, i) => (
              <div
                key={s.label}
                className="py-5 pr-6"
                style={{
                  borderRight: i < 3 ? "1px solid #e5e5e5" : "none",
                  paddingLeft: i > 0 ? "24px" : "0",
                }}
              >
                <p className="font-mono text-[26px] font-bold text-shell-text tracking-tight mb-1">
                  {s.value}
                </p>
                <p className="font-mono text-[10px] text-shell-muted tracking-[0.08em]">
                  {s.label.toUpperCase()}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Pair snapshot */}
        <section className="max-w-[1152px] mx-auto px-6 py-16">
          <div className="flex items-baseline justify-between mb-6">
            <div>
              <h2 className="font-sans font-bold text-xl text-shell-text tracking-tight">
                Live Regime Snapshot
              </h2>
              <p className="font-mono text-[11px] text-shell-muted mt-1.5">
                {today} · Updated daily
              </p>
            </div>
            <Link
              href="/terminal"
              className="font-mono text-[11px] text-shell-secondary border border-shell-border px-3.5 py-1.5"
            >
              Open terminal →
            </Link>
          </div>
          <div
            className="grid gap-px"
            style={{
              gridTemplateColumns: `repeat(${PAIRS.length}, 1fr)`,
              background: "#e5e5e5",
              boxShadow: "0 0 0 1px #e5e5e5",
            }}
          >
            {PAIRS.map((p) => (
              <PairCard
                key={p.label}
                pair={p}
                call={(calls[p.label] as LatestRegimeCall | undefined) ?? null}
                signals={(signals[p.label] as LatestSignal | undefined) ?? null}
              />
            ))}
          </div>
        </section>

        {/* Regime heatmap */}
        <section className="max-w-[1152px] mx-auto px-6 pb-12">
          <div className="flex items-baseline justify-between mb-5">
            <div>
              <h2 className="font-sans font-bold text-xl text-shell-text tracking-tight">
                30-Day Regime View
              </h2>
              <p className="font-mono text-[11px] text-shell-muted mt-1.5">
                Cross-pair regime at a glance. Click a pair for detail.
              </p>
            </div>
          </div>
          <RegimeHeatmap heatmap={null} />
        </section>

        {/* Validation strip */}
        <section className="bg-[#0a0a0a] border-t border-b border-[#111]">
          <div className="max-w-[1152px] mx-auto px-6 py-14">
            <div className="flex items-start justify-between mb-7 flex-wrap gap-5">
              <div>
                <p className="font-mono text-[10px] text-[#444] tracking-[0.12em] mb-2">
                  VALIDATION LOG
                </p>
                <h2 className="font-sans font-bold text-xl text-[#f2f2f2] tracking-tight">
                  Next-day outcome, on the record.
                </h2>
                <p className="font-sans text-[13px] text-[#525252] mt-2">
                  Every call validated the following trading day. No revisions,
                  no ex-post edits.
                </p>
              </div>
              <div className="text-right">
                <p className="font-mono text-[36px] font-bold text-up tracking-tight leading-none">
                  {accuracy}%
                </p>
                <p className="font-mono text-[10px] text-[#444] tracking-[0.1em] mt-1">
                  7-DAY ACCURACY
                </p>
              </div>
            </div>
            <ValidationTable rows={validation} tone="dark" />
            <Link
              href="/performance"
              className="inline-block font-mono text-[11px] text-[#555] border border-[#1f1f1f] px-4 py-2 mt-4"
            >
              Full validation log →
            </Link>
          </div>
        </section>

        {/* Signal Architecture */}
        <section className="max-w-[1152px] mx-auto px-6 py-16">
          <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-16 items-start">
            <div>
              <p className="font-mono text-[10px] text-shell-muted tracking-[0.12em] mb-3.5">
                SIGNAL ARCHITECTURE
              </p>
              <h2 className="font-sans font-bold text-[28px] text-shell-text tracking-tight leading-snug mb-4">
                Four signal
                <br />
                families. One
                <br />
                composite.
              </h2>
              <p className="font-sans text-sm text-shell-secondary leading-relaxed">
                Each family is normalized to a percentile rank before weighting.
                The composite drives the regime label.
              </p>
            </div>
            <div className="border border-shell-border">
              {[
                {
                  n: "01",
                  label: "Rate Differentials",
                  desc: "2Y sovereign yield spreads. Primary driver of medium-term FX regime direction.",
                  color: "#4BA3E3",
                },
                {
                  n: "02",
                  label: "COT Positioning",
                  desc: "CFTC weekly non-commercial net positions as percentile ranks. Crowd and reversal signals.",
                  color: "#F5923A",
                },
                {
                  n: "03",
                  label: "Realized Volatility",
                  desc: "5d and 20d realized vs 30d implied. Vol gate forces VOL_EXPANDING above 90th pctile.",
                  color: "#D94030",
                },
                {
                  n: "04",
                  label: "OI and Risk Reversals",
                  desc: "Open interest flows and 25-delta risk reversals. INR-specific series included.",
                  color: "#888",
                },
              ].map((s, i) => (
                <div
                  key={s.n}
                  className="flex items-start gap-5 px-5 py-5"
                  style={{
                    borderBottom: i < 3 ? "1px solid #e5e5e5" : "none",
                  }}
                >
                  <span
                    className="font-mono text-[11px] font-bold min-w-[24px] pt-0.5"
                    style={{ color: s.color }}
                  >
                    {s.n}
                  </span>
                  <div>
                    <p className="font-sans font-semibold text-sm text-shell-text mb-1">
                      {s.label}
                    </p>
                    <p className="font-sans text-[13px] text-shell-secondary leading-relaxed">
                      {s.desc}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* About strip */}
        <section className="border-t border-b border-shell-border">
          <div className="max-w-[1152px] mx-auto px-6 py-12 grid grid-cols-1 md:grid-cols-[1fr_2fr] gap-16 items-start">
            <div>
              <p className="font-mono text-[10px] text-shell-muted tracking-[0.12em] mb-3.5">
                ABOUT
              </p>
              <h2 className="font-sans font-bold text-[22px] text-shell-text tracking-tight">
                Shreyash Sakhare
              </h2>
              <p className="font-mono text-[11px] text-shell-muted mt-1.5">
                EE Undergrad · Discretionary Macro Research
              </p>
            </div>
            <div>
              <p className="font-sans text-[15px] text-shell-secondary leading-relaxed max-w-[580px] mb-5">
                Studying how G10 FX regimes form and break using rate
                differentials, COT positioning, and volatility. This site is the
                public trace of that work — dated calls, validated outcomes, no
                narrative added after the fact.
              </p>
              <div className="flex gap-5">
                <Link
                  href="/about"
                  className="font-sans text-[13px] font-medium text-shell-text border border-shell-border px-4 py-2"
                >
                  About this project
                </Link>
                <Link
                  href="/brief"
                  className="font-sans text-[13px] font-medium text-shell-secondary underline decoration-[#d0d0d0] underline-offset-4 py-2"
                >
                  Today&apos;s brief →
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
