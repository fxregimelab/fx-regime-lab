import { AccuracyMilestoneTracker } from "@/components/performance/AccuracyMilestoneTracker";
import { BrierChart } from "@/components/performance/BrierChart";
import { PairBreakdownTable } from "@/components/performance/PairBreakdownTable";
import { PerformanceUrlSync } from "@/components/performance/PerformanceUrlSync";
import { RegimeBreakdown } from "@/components/performance/RegimeBreakdown";
import { StatsCard } from "@/components/performance/StatsCard";
import { ValidationTable } from "@/components/regime/ValidationTable";
import { Footer } from "@/components/shell/Footer";
import { Nav } from "@/components/shell/Nav";
import { AuditTrailBannerServer } from "@/components/ui/audit-trail-banner";
import { fmtMeanCI, fmtPropCI, meanCI, wilsonCI } from "@/lib/stats";
import {
  getRegimeBreakdown,
  getValidationLogT5T20,
  getValidationStats,
} from "@/lib/supabase/queries";
import type { ValidationRowT5, ValidationStats } from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Performance | FX Regime Lab",
  description:
    "T+5 and T+20 validation track record. Brier scores, win rates, Sharpe-like ratios, and calibration analysis.",
};

/* ─── helpers ───────────────────────────────────────────────────────────── */

function fmtPctRaw(n: number | null | undefined, digits = 1) {
  if (n == null) return "—";
  // Defensive: DB may store proportions (0–1) or percentages (>1)
  const prop = n > 1 ? n / 100 : n;
  const sign = prop >= 0 ? "+" : "";
  return `${sign}${(prop * 100).toFixed(digits)}%`;
}

function fmtBrier(n: number | null | undefined) {
  if (n == null) return "—";
  return n.toFixed(3);
}

/* ─── SVG equity curve ──────────────────────────────────────────────────── */

function EquityCurveSVG({
  data,
}: {
  data: { date: string; value: number }[];
}) {
  if (data.length < 2) {
    return (
      <div className="w-full h-[240px] md:h-[320px] lg:h-[400px] bg-black flex items-center justify-center">
        <span className="font-mono text-[10px] text-[var(--color-text-muted)] tracking-wider">
          INSUFFICIENT DATA (N &lt; 2)
        </span>
      </div>
    );
  }

  const W = 1000;
  const H = 400;
  const padL = 60;
  const padR = 16;
  const padT = 16;
  const padB = 32;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;

  const values = data.map((d) => d.value);
  let minV = Math.min(...values);
  let maxV = Math.max(...values);
  if (minV === maxV) {
    minV -= 0.5;
    maxV += 0.5;
  }
  const range = maxV - minV || 1;

  const peak: number[] = [];
  let p = Number.NEGATIVE_INFINITY;
  for (const v of values) {
    if (v > p) p = v;
    peak.push(p);
  }

  const pts = data.map((d, i) => {
    const x = padL + (i / (data.length - 1)) * chartW;
    const y = padT + chartH - ((d.value - minV) / range) * chartH;
    const yPeak = padT + chartH - ((peak[i] - minV) / range) * chartH;
    return { x, y, yPeak, date: d.date };
  });

  const lineD = pts
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(" ");

  const areaD = `M ${pts[0].x.toFixed(1)} ${padT + chartH} ${pts.map((p) => `L ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ")} L ${pts[pts.length - 1].x.toFixed(1)} ${padT + chartH} Z`;

  const ddD = `${lineD} ${pts
    .slice()
    .reverse()
    .map((p) => `L ${p.x.toFixed(1)} ${p.yPeak.toFixed(1)}`)
    .join(" ")} Z`;

  const yTicks = [maxV, (minV + maxV) / 2, minV];
  const xStep = Math.max(1, Math.floor(data.length / 5));
  const xLabels = pts.filter(
    (_, i) => i % xStep === 0 || i === data.length - 1,
  );

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      className="w-full h-[240px] md:h-[320px] lg:h-[400px] block"
    >
      <title>Performance Chart</title>
      <rect width={W} height={H} fill="#000000" />

      {yTicks.map((v, i) => {
        const y = padT + chartH - ((v - minV) / range) * chartH;
        return (
          <line
            key={`grid-${v}`}
            x1={padL}
            y1={y}
            x2={W - padR}
            y2={y}
            stroke="#111111"
            strokeWidth={1}
          />
        );
      })}

      <path d={areaD} fill="rgba(214,211,209,0.08)" />
      <path d={ddD} fill="rgba(184,122,122,0.06)" />

      <path
        d={lineD}
        fill="none"
        stroke="#d6d3d1"
        strokeWidth={2}
        vectorEffect="non-scaling-stroke"
      />

      {yTicks.map((v) => {
        const y = padT + chartH - ((v - minV) / range) * chartH;
        return (
          <text
            key={`ylabel-${v}`}
            x={padL - 8}
            y={y + 3}
            textAnchor="end"
            fill="#8a8a8a"
            fontSize={10}
            fontFamily="JetBrains Mono, monospace"
            style={{ fontVariantNumeric: "tabular-nums" }}
          >
            {fmtPctRaw(v)}
          </text>
        );
      })}

      {xLabels.map((p) => (
        <text
          key={`xlabel-${p.date}`}
          x={p.x}
          y={H - 10}
          textAnchor="middle"
          fill="#8a8a8a"
          fontSize={10}
          fontFamily="JetBrains Mono, monospace"
          style={{ fontVariantNumeric: "tabular-nums" }}
        >
          {p.date}
        </text>
      ))}
    </svg>
  );
}

/* ─── page ──────────────────────────────────────────────────────────────── */

export const dynamic = "force-dynamic";

/* ─── compute stats from filtered validation log ─────────────────────────── */

function computeStatsFromLog(
  rows: ValidationRowT5[],
  pair: string | null,
  horizon: "t5" | "t20",
): ValidationStats {
  const filtered = pair ? rows.filter((r) => r.pair === pair) : rows;

  const outcomeKey = horizon === "t5" ? "t5Outcome" : "t20Outcome";
  const brierKey = horizon === "t5" ? "t5Brier" : "t20Brier";
  const returnKey = horizon === "t5" ? "t5ReturnBps" : "t20ReturnBps";

  const valid = filtered.filter(
    (r) =>
      r[outcomeKey as keyof ValidationRowT5] === "CORRECT" ||
      r[outcomeKey as keyof ValidationRowT5] === "WRONG",
  );
  const wins = valid.filter(
    (r) => r[outcomeKey as keyof ValidationRowT5] === "CORRECT",
  ).length;
  const sampleSize = valid.length;
  const winRate = sampleSize > 0 ? wins / sampleSize : null;

  const brierValues = filtered
    .map((r) => r[brierKey as keyof ValidationRowT5] as number | null)
    .filter((v): v is number => v != null);
  const brierScore =
    brierValues.length > 0
      ? brierValues.reduce((s, v) => s + v, 0) / brierValues.length
      : null;

  const returns = filtered
    .map((r) => r[returnKey as keyof ValidationRowT5] as number | null)
    .filter((v): v is number => v != null);
  const avgReturnBps =
    returns.length > 0
      ? returns.reduce((s, v) => s + v, 0) / returns.length
      : null;

  let sharpeLike: number | null = null;
  if (avgReturnBps != null && returns.length > 1) {
    const mean = avgReturnBps;
    const variance =
      returns.reduce((s, v) => s + (v - mean) ** 2, 0) / (returns.length - 1);
    sharpeLike = variance > 0 ? mean / Math.sqrt(variance) : null;
  }

  // Rolling 90d: production data is only ~40 days old, so this equals
  // all-time production accuracy for now.
  const sortedDates = [...filtered.map((r) => r.date)].sort();
  const latestDate =
    sortedDates.length > 0 ? sortedDates[sortedDates.length - 1] : "";
  const cutoff90d = new Date(latestDate || Date.now());
  cutoff90d.setDate(cutoff90d.getDate() - 90);
  const cutoffStr = cutoff90d.toISOString().split("T")[0];
  const recent90 = valid.filter((r) => r.date >= cutoffStr);
  const rolling90dAccuracy =
    recent90.length > 0
      ? recent90.filter(
          (r) => r[outcomeKey as keyof ValidationRowT5] === "CORRECT",
        ).length / recent90.length
      : null;

  return {
    pair: pair ?? "ALL",
    horizon,
    winRate,
    wins,
    brierScore,
    sampleSize,
    avgReturnBps,
    sharpeLike,
    rolling90dAccuracy,
    asOfDate: latestDate,
  };
}

export default async function PerformancePage() {
  const supabase = await createClient();
  const [statsT5Raw, statsT20Raw, validation, regimeBreakdown] =
    await Promise.all([
      getValidationStats(supabase, "t5"),
      getValidationStats(supabase, "t20"),
      getValidationLogT5T20(supabase, 500),
      getRegimeBreakdown(supabase, 500),
    ]);

  // Compute ALL stats from filtered validation log (production period only)
  const allT5 = computeStatsFromLog(validation, null, "t5");
  const allT20 = computeStatsFromLog(validation, null, "t20");
  const totalCalls = allT5.sampleSize ?? validation.length;

  // Compute per-pair stats from filtered validation log
  const PAIR_LABELS = ["EUR/USD", "USD/JPY", "USD/INR"] as const;
  const computedT5 = PAIR_LABELS.map((p) =>
    computeStatsFromLog(validation, p, "t5"),
  );
  const computedT20 = PAIR_LABELS.map((p) =>
    computeStatsFromLog(validation, p, "t20"),
  );

  // Merge computed stats with raw stats: prefer computed (production-only),
  // but keep raw per-pair rows as fallback for fields we don't compute.
  const t5Map = new Map(
    statsT5Raw.filter((s) => s.pair !== "ALL").map((s) => [s.pair, s]),
  );
  const t20Map = new Map(
    statsT20Raw.filter((s) => s.pair !== "ALL").map((s) => [s.pair, s]),
  );

  const statsT5: ValidationStats[] = [
    ...computedT5.map((computed) => {
      const raw = t5Map.get(computed.pair);
      return raw
        ? {
            ...raw,
            winRate: computed.winRate,
            wins: computed.wins,
            brierScore: computed.brierScore,
            sampleSize: computed.sampleSize,
            avgReturnBps: computed.avgReturnBps,
            sharpeLike: computed.sharpeLike,
            rolling90dAccuracy: computed.rolling90dAccuracy,
            asOfDate: computed.asOfDate,
          }
        : computed;
    }),
    allT5,
  ];
  const statsT20: ValidationStats[] = [
    ...computedT20.map((computed) => {
      const raw = t20Map.get(computed.pair);
      return raw
        ? {
            ...raw,
            winRate: computed.winRate,
            wins: computed.wins,
            brierScore: computed.brierScore,
            sampleSize: computed.sampleSize,
            avgReturnBps: computed.avgReturnBps,
            sharpeLike: computed.sharpeLike,
            rolling90dAccuracy: computed.rolling90dAccuracy,
            asOfDate: computed.asOfDate,
          }
        : computed;
    }),
    allT20,
  ];

  // equity curve from T+5 cumulative log-returns (bps)
  const sortedAsc = [...validation].sort((a, b) =>
    a.date.localeCompare(b.date),
  );
  const byDate = new Map<string, number>();
  for (const r of sortedAsc) {
    if (r.t5ReturnBps != null) {
      byDate.set(r.date, (byDate.get(r.date) ?? 0) + r.t5ReturnBps);
    }
  }
  const dates = [...byDate.keys()].sort();
  let cum = 0;
  const equityCurve = dates.map((d) => {
    const daily = byDate.get(d) ?? 0;
    cum += daily;
    return { date: d, value: cum };
  });

  // max drawdown
  let peakVal = Number.NEGATIVE_INFINITY;
  let maxDD = 0;
  for (const pt of equityCurve) {
    if (pt.value > peakVal) peakVal = pt.value;
    const dd = peakVal - pt.value;
    if (dd > maxDD) maxDD = dd;
  }

  // rolling 10-call Brier score
  const brierSeries: { date: string; value: number }[] = [];
  for (let i = 0; i < sortedAsc.length; i++) {
    const window = sortedAsc.slice(Math.max(0, i - 9), i + 1);
    const valid = window.filter((r) => r.t5Brier != null);
    if (valid.length > 0) {
      const avg =
        valid.reduce((s, r) => s + (r.t5Brier ?? 0), 0) / valid.length;
      brierSeries.push({ date: valid[valid.length - 1].date, value: avg });
    }
  }

  // freshness — use latest validation_stats as_of_date (more current than
  // T+5 validation_log which lags by ~5 business days).
  const latestStatsDate = statsT5[0]?.asOfDate ?? null;
  const lastDate =
    latestStatsDate ?? (dates.length > 0 ? dates[dates.length - 1] : null);
  const STALE_THRESHOLD_DAYS = 10;
  const isStale = lastDate
    ? new Date().getTime() - new Date(lastDate).getTime() >
      STALE_THRESHOLD_DAYS * 24 * 60 * 60 * 1000
    : true;

  // ── 95% confidence intervals ────────────────────────────────────────────
  const t5WinCI = wilsonCI(allT5?.wins ?? 0, allT5?.sampleSize ?? 0);
  const t20WinCI = wilsonCI(allT20?.wins ?? 0, allT20?.sampleSize ?? 0);

  const t5BrierValues = validation
    .map((r) => r.t5Brier)
    .filter((v): v is number => v != null);
  const t20BrierValues = validation
    .map((r) => r.t20Brier)
    .filter((v): v is number => v != null);
  const t5BrierCI = meanCI(t5BrierValues);
  const t20BrierCI = meanCI(t20BrierValues);

  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      <PerformanceUrlSync />
      <Nav />
      <AuditTrailBannerServer variant="shell" />
      <main
        id="main-content"
        className="max-w-[1152px] mx-auto px-6 pt-28 pb-20 w-full"
      >
        {/* ── Header ─────────────────────────────────────────────────────── */}
        <div className="mb-10 pb-6 border-b border-[var(--color-border)]">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <p className="font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-2.5">
                Track Record
              </p>
              <h1 className="font-sans font-semibold text-[32px] text-[var(--color-text)] tracking-tight">
                Performance
              </h1>
              <p className="font-sans text-[15px] text-[var(--color-text-secondary)] mt-2 leading-[1.6]">
                T+5 and T+20 directional validation. Updated daily after market
                close.
              </p>
            </div>
            {lastDate && (
              <div className="flex items-center gap-2 mt-2">
                {isStale && (
                  <span className="font-mono text-[9px] tracking-widest text-[var(--color-warn)] border border-[var(--color-warn)] px-1.5 py-0.5">
                    STALE
                  </span>
                )}
                <span className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-wider tabular-nums">
                  UPDATED {lastDate}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* ── Summary Metrics ────────────────────────────────────────────── */}
        <div
          className={`grid grid-cols-2 md:grid-cols-5 gap-px bg-[var(--color-border)] border border-[var(--color-border)] mb-10 ${isStale ? "opacity-50" : ""}`}
        >
          <StatsCard
            label="T+5 WIN RATE"
            value={fmtPctRaw(allT5?.winRate)}
            sub="calls"
            sampleSize={allT5?.sampleSize}
            ci={fmtPropCI(allT5?.winRate ?? null, t5WinCI)}
          />
          <StatsCard
            label="T+5 BRIER"
            value={fmtBrier(allT5?.brierScore)}
            sub={
              allT5?.brierScore != null
                ? allT5.brierScore < 0.1
                  ? "Excellent"
                  : allT5.brierScore < 0.2
                    ? "Good"
                    : allT5.brierScore < 0.3
                      ? "Fair"
                      : "Poor"
                : undefined
            }
            sampleSize={allT5?.sampleSize}
            ci={fmtMeanCI(allT5?.brierScore ?? null, t5BrierCI)}
          />
          <StatsCard
            label="T+20 WIN RATE"
            value={fmtPctRaw(allT20?.winRate)}
            sub="calls"
            sampleSize={allT20?.sampleSize}
            ci={fmtPropCI(allT20?.winRate ?? null, t20WinCI)}
          />
          <StatsCard
            label="T+20 BRIER"
            value={fmtBrier(allT20?.brierScore)}
            sub={
              allT20?.brierScore != null
                ? allT20.brierScore < 0.1
                  ? "Excellent"
                  : allT20.brierScore < 0.2
                    ? "Good"
                    : allT20.brierScore < 0.3
                      ? "Fair"
                      : "Poor"
                : undefined
            }
            sampleSize={allT20?.sampleSize}
            ci={fmtMeanCI(allT20?.brierScore ?? null, t20BrierCI)}
          />
          <StatsCard
            label="T+5 VALIDATED"
            value={`${totalCalls}`}
            sub="calls with T+5 outcomes"
          />
        </div>

        {/* ── Accuracy Milestone Tracker ─────────────────────────────────── */}
        {(() => {
          const eurT5 = statsT5.find((s) => s.pair === "EURUSD");
          const acc = eurT5?.rolling90dAccuracy ?? null;
          if (acc == null) return null;

          // Build real rolling accuracy history from validation records
          const eurRecords = validation
            .filter(
              (r) =>
                r.pair === "EUR/USD" &&
                (r.t5Outcome === "CORRECT" || r.t5Outcome === "WRONG"),
            )
            .sort((a, b) => a.date.localeCompare(b.date));

          const windowSize = 10;
          const history = [] as { date: string; accuracy: number }[];
          for (let i = 0; i < eurRecords.length; i++) {
            const window = eurRecords.slice(
              Math.max(0, i - windowSize + 1),
              i + 1,
            );
            const correct = window.filter(
              (r) => r.t5Outcome === "CORRECT",
            ).length;
            history.push({
              date: eurRecords[i].date,
              accuracy: correct / window.length,
            });
          }

          // Take last 30 points
          const recent = history.slice(-30);
          if (recent.length === 0) return null;

          return (
            <div className="mb-10">
              <AccuracyMilestoneTracker
                currentAccuracy={acc}
                history={recent}
                daysAboveGate={recent.filter((h) => h.accuracy >= 0.55).length}
                currentStreak={
                  recent[recent.length - 1].accuracy >= 0.55
                    ? recent
                        .slice()
                        .reverse()
                        .findIndex((h) => h.accuracy < 0.55)
                    : -recent
                        .slice()
                        .reverse()
                        .findIndex((h) => h.accuracy >= 0.55)
                }
                bestWindowAccuracy={Math.max(...recent.map((h) => h.accuracy))}
              />
            </div>
          );
        })()}

        {/* ── Equity Curve ───────────────────────────────────────────────── */}
        <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
          <div className="px-5 py-3 border-b border-[var(--color-border)] flex items-center justify-between">
            <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
              Equity Curve — Cumulative T+5 Log-Return (bps)
            </p>
            <div className="flex items-center gap-4">
              <span className="font-mono text-[10px] text-[var(--color-text-muted)] tabular-nums">
                Max DD:{" "}
                <span style={{ color: "var(--color-down)" }}>
                  {fmtPctRaw(-maxDD / 100)}
                </span>
              </span>
            </div>
          </div>
          <EquityCurveSVG data={equityCurve} />
        </div>

        {/* ── Brier Score Time Series ────────────────────────────────────── */}
        <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
          <div className="px-5 py-3 border-b border-[var(--color-border)]">
            <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
              Rolling 10-Call Brier Score
            </p>
          </div>
          <BrierChart data={brierSeries} />
        </div>

        {/* ── Regime Breakdown ───────────────────────────────────────────── */}
        <RegimeBreakdown rows={regimeBreakdown} horizon="t5" />
        <RegimeBreakdown rows={regimeBreakdown} horizon="t20" />

        {/* ── Per-Pair Breakdown ─────────────────────────────────────────── */}
        <div className="mb-10">
          <PairBreakdownTable statsT5={statsT5} statsT20={statsT20} />
        </div>

        {/* ── Validation History ─────────────────────────────────────────── */}
        <div className="mb-10">
          <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-4">
            Validation History — T+5 / T+20
          </p>
          <ValidationTable rows={validation} tone="dark" mode="t5t20" />
        </div>

        {/* ── Disclaimer ─────────────────────────────────────────────────── */}
        <p className="font-mono text-[10px] text-[var(--color-text-muted)] tracking-wider leading-relaxed pt-5 mt-5 border-t border-[var(--color-border)]">
          T+5 AND T+20 DIRECTIONAL OUTCOMES. RETURNS ARE LOG-RETURNS IN BASIS
          POINTS RELATIVE TO CALL DIRECTION. RESEARCH ONLY — NOT INVESTMENT
          ADVICE.
        </p>
      </main>
      <Footer />
    </div>
  );
}
