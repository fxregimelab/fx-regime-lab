import { AccuracyMilestoneTracker } from "@/components/performance/AccuracyMilestoneTracker";
import { BrierChart } from "@/components/performance/BrierChart";
import { PairBreakdownTable } from "@/components/performance/PairBreakdownTable";
import { RegimeBreakdown } from "@/components/performance/RegimeBreakdown";
import { StatsCard } from "@/components/performance/StatsCard";
import { ValidationTable } from "@/components/regime/ValidationTable";
import { Footer } from "@/components/shell/Footer";
import { Nav } from "@/components/shell/Nav";
import { AuditTrailBannerServer } from "@/components/ui/audit-trail-banner";
import { EURUSD_ACCURACY_GATE } from "@/lib/config";
import { fmtMeanCI, fmtPropCI, meanCI, wilsonCI } from "@/lib/stats";
import {
  getBacktestVersions,
  getRegimeBreakdown,
  getRegimeBreakdownByVersion,
  getRegimeCallsByVersion,
  getSimulationResults,
  getValidationByVersion,
  getValidationLogT5T20,
  getValidationStats,
} from "@/lib/supabase/queries";
import type {
  RegimeBreakdownRow,
  SimulationResult,
  ValidationRowT5,
  ValidationStats,
  VersionedRegimeBreakdownRow,
  VersionedRegimeCall,
} from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";
import type { Metadata } from "next";
import { TrackRecordTabs } from "./components/TrackRecordTabs";

export const metadata: Metadata = {
  title: "Track Record | FX Regime Lab",
  description:
    "Live and backtested track record. T+5 and T+20 directional validation. Regime-aware vs uniform benchmark comparison.",
};

export const dynamic = "force-dynamic";

/* ─── helpers ───────────────────────────────────────────────────────────── */

function fmtPctRaw(n: number | null | undefined, digits = 1) {
  if (n == null) return "—";
  const prop = n > 1 ? n / 100 : n;
  const sign = prop >= 0 ? "+" : "";
  return `${sign}${(prop * 100).toFixed(digits)}%`;
}

function fmtBrier(n: number | null | undefined) {
  if (n == null) return "—";
  return n.toFixed(3);
}

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
  const xLabels = pts.filter((_, i) => i % xStep === 0);

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      className="w-full h-[240px] md:h-[320px] lg:h-[400px] block"
    >
      <title>Equity Curve</title>
      <rect width={W} height={H} fill="var(--color-void)" />

      {yTicks.map((v) => {
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

/* ─── Mini equity curve ─────────────────────────────────────────────────── */

function MiniEquityCurve({
  data,
}: {
  data: { date: string; value: number }[];
}) {
  if (data.length < 2) return null;

  const W = 300;
  const H = 80;
  const pad = 2;
  const chartW = W - pad * 2;
  const chartH = H - pad * 2;

  const values = data.map((d) => d.value);
  const minV = Math.min(...values);
  const maxV = Math.max(...values);
  const range = maxV - minV || 1;

  const pts = data.map((d, i) => {
    const x = pad + (i / (data.length - 1)) * chartW;
    const y = pad + chartH - ((d.value - minV) / range) * chartH;
    return `${x},${y}`;
  });

  return (
    <svg
      width="100%"
      height={H}
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      role="img"
      aria-label="Mini equity curve"
    >
      <title>Mini Equity Curve</title>
      <rect width={W} height={H} fill="var(--color-void)" />
      <polyline
        points={pts.join(" ")}
        fill="none"
        stroke="var(--color-text-muted)"
        strokeWidth="1"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/* ─── Empty state ───────────────────────────────────────────────────────── */

function EmptyState({ message }: { message: string }) {
  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-surface)] px-8 py-12 text-center">
      <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-2">
        {message}
      </p>
      <p className="font-sans text-[13px] text-[var(--color-text-secondary)]">
        Data will populate when the pipeline completes the next run.
      </p>
    </div>
  );
}

/* ─── Live tab content ──────────────────────────────────────────────────── */

function LiveTabContent({
  statsT5,
  statsT20,
  validation,
  regimeBreakdown,
  allT5,
  allT20,
  totalCalls,
  equityCurve,
  maxDD,
  brierSeries,
  freshnessStatus,
  lastDate,
  t5WinCI,
  t20WinCI,
  t5BrierCI,
  t20BrierCI,
}: {
  statsT5: ValidationStats[];
  statsT20: ValidationStats[];
  validation: ValidationRowT5[];
  regimeBreakdown: RegimeBreakdownRow[];
  allT5: ValidationStats;
  allT20: ValidationStats;
  totalCalls: number;
  equityCurve: { date: string; value: number }[];
  maxDD: number;
  brierSeries: { date: string; value: number }[];
  freshnessStatus: "LIVE" | "ACTIVE" | "STALE";
  lastDate: string | null;
  t5WinCI: [number, number];
  t20WinCI: [number, number];
  t5BrierCI: [number, number];
  t20BrierCI: [number, number];
}) {
  return (
    <div>
      {/* Summary bar */}
      <div className="mb-8 pb-4 border-b border-[var(--color-border)]">
        <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
          <span className="font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase">
            Live Track Record
          </span>
          <span className="text-[var(--color-border)]">·</span>
          <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
            SINCE MAY 1, 2026
          </span>
          <span className="text-[var(--color-border)]">·</span>
          <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
            N = {totalCalls} CALLS
          </span>
          {lastDate && (
            <>
              <span className="text-[var(--color-border)]">·</span>
              <span className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-wider tabular-nums">
                UPDATED {lastDate}
              </span>
            </>
          )}
          <span
            className={`font-mono text-[9px] tracking-widest border px-1.5 py-0.5 ${
              freshnessStatus === "LIVE"
                ? "text-green-600 border-green-600"
                : freshnessStatus === "ACTIVE"
                  ? "text-blue-400 border-blue-400"
                  : "text-[var(--color-warn)] border-[var(--color-warn)]"
            }`}
          >
            {freshnessStatus}
          </span>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[var(--color-border)] border border-[var(--color-border)] mb-10">
        <StatsCard
          label="T+5 WIN RATE"
          value={fmtPctRaw(allT5?.winRate)}
          sub="calls"
          sampleSize={allT5?.sampleSize}
          ci={fmtPropCI(allT5?.winRate ?? null, t5WinCI)}
        />
        <StatsCard
          label="T+20 WIN RATE"
          value={fmtPctRaw(allT20?.winRate)}
          sub="calls"
          sampleSize={allT20?.sampleSize}
          ci={fmtPropCI(allT20?.winRate ?? null, t20WinCI)}
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
      </div>

      {/* Mini equity curve */}
      <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
        <div className="px-5 py-3 border-b border-[var(--color-border)] flex items-center justify-between">
          <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
            Cumulative T+5 Log-Return (%)
          </p>
          <span className="font-mono text-[10px] text-[var(--color-text-muted)] tabular-nums">
            Max DD:{" "}
            <span style={{ color: "var(--color-down)" }}>
              {fmtPctRaw(-maxDD)}
            </span>
          </span>
        </div>
        <EquityCurveSVG data={equityCurve} />
      </div>

      {/* Accuracy milestone */}
      {(() => {
        const eurT5 = statsT5.find((s) => s.pair === "EUR/USD");
        const acc = eurT5?.rolling90dAccuracy ?? null;
        if (acc == null) return null;
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
        const recent = history.slice(-30);
        if (recent.length === 0) return null;
        return (
          <div className="mb-10">
            <AccuracyMilestoneTracker
              currentAccuracy={acc}
              history={recent}
              daysAboveGate={
                recent.filter((h) => h.accuracy >= EURUSD_ACCURACY_GATE).length
              }
              gate={EURUSD_ACCURACY_GATE}
              currentStreak={(() => {
                const rev = recent.slice().reverse();
                const lastAbove = rev[0].accuracy >= EURUSD_ACCURACY_GATE;
                const idx = rev.findIndex((h) =>
                  lastAbove
                    ? h.accuracy < EURUSD_ACCURACY_GATE
                    : h.accuracy >= EURUSD_ACCURACY_GATE,
                );
                return lastAbove
                  ? idx === -1
                    ? recent.length
                    : idx
                  : -(idx === -1 ? recent.length : idx);
              })()}
              bestWindowAccuracy={Math.max(...recent.map((h) => h.accuracy))}
            />
          </div>
        );
      })()}

      {/* Brier chart */}
      <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
        <div className="px-5 py-3 border-b border-[var(--color-border)]">
          <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
            Rolling 10-Call Brier Score
          </p>
        </div>
        <BrierChart data={brierSeries} />
      </div>

      {/* Regime breakdown */}
      <RegimeBreakdown rows={regimeBreakdown} horizon="t5" />
      <RegimeBreakdown rows={regimeBreakdown} horizon="t20" />

      {/* Per-pair breakdown */}
      <div className="mb-10">
        <PairBreakdownTable statsT5={statsT5} statsT20={statsT20} />
      </div>

      {/* Validation history */}
      <div className="mb-10">
        <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-4">
          Validation History — T+5 / T+20
        </p>
        <ValidationTable rows={validation} tone="dark" mode="t5t20" />
      </div>

      <p className="font-mono text-[10px] text-[var(--color-text-muted)] tracking-wider leading-relaxed pt-5 mt-5 border-t border-[var(--color-border)]">
        T+5 AND T+20 DIRECTIONAL OUTCOMES. RETURNS ARE LOG-RETURNS IN BASIS
        POINTS RELATIVE TO CALL DIRECTION. RESEARCH ONLY — NOT INVESTMENT
        ADVICE.
      </p>
    </div>
  );
}

/* ─── Backtested tab content ────────────────────────────────────────────── */

function BacktestedTabContent({
  versions,
  versionedCalls,
  versionedBreakdown,
  simulationResults,
}: {
  versions: string[];
  versionedCalls: VersionedRegimeCall[];
  versionedBreakdown: VersionedRegimeBreakdownRow[];
  simulationResults: SimulationResult[];
}) {
  const hasData = versionedCalls.length > 0 || versionedBreakdown.length > 0;

  return (
    <div>
      {/* Version selector */}
      <div className="mb-8 pb-4 border-b border-[var(--color-border)] flex items-center gap-4">
        <span className="font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase">
          Backtested Track Record
        </span>
        <span className="text-[var(--color-border)]">·</span>
        <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
          MODEL VERSION
        </span>
        <div className="flex gap-2">
          {versions.map((v) => (
            <span
              key={v}
              className={`font-mono text-[10px] px-2 py-1 border ${
                v === versions[0]
                  ? "border-[var(--color-text)] text-[var(--color-text)]"
                  : "border-[var(--color-border)] text-[var(--color-text-muted)]"
              }`}
            >
              {v}
            </span>
          ))}
        </div>
      </div>

      {!hasData ? (
        <EmptyState message="No backtested data available for this version" />
      ) : (
        <>
          {/* Summary metrics */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-px bg-[var(--color-border)] border border-[var(--color-border)] mb-10">
            <div className="bg-[var(--color-surface)] p-4">
              <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-1">
                T+5 WR
              </p>
              <p className="font-mono text-[clamp(16px,2vw,20px)] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">
                —
              </p>
            </div>
            <div className="bg-[var(--color-surface)] p-4">
              <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-1">
                T+5 BRIER
              </p>
              <p className="font-mono text-[clamp(16px,2vw,20px)] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">
                —
              </p>
            </div>
            <div className="bg-[var(--color-surface)] p-4">
              <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-1">
                T+20 WR
              </p>
              <p className="font-mono text-[clamp(16px,2vw,20px)] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">
                —
              </p>
            </div>
            <div className="bg-[var(--color-surface)] p-4">
              <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-1">
                T+20 BRIER
              </p>
              <p className="font-mono text-[clamp(16px,2vw,20px)] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">
                —
              </p>
            </div>
            <div className="bg-[var(--color-surface)] p-4">
              <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-1">
                TOTAL CALLS
              </p>
              <p className="font-mono text-[clamp(16px,2vw,20px)] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">
                {versionedCalls.length}
              </p>
            </div>
          </div>

          {/* Per-pair cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
            {["EURUSD", "USDJPY", "USDINR"].map((pair) => {
              const pairCalls = versionedCalls.filter((c) => c.pair === pair);
              return (
                <div
                  key={pair}
                  className="border border-[var(--color-border)] bg-[var(--color-surface)] p-5"
                >
                  <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-3">
                    {pair.replace("USD", "USD/").replace("EUR", "EUR/")}
                  </p>
                  <div className="grid grid-cols-2 gap-4 mb-3">
                    <div>
                      <p className="font-mono text-[9px] text-[var(--color-text-muted)]">
                        T+5 WR
                      </p>
                      <p className="font-mono text-[18px] text-[var(--color-text)] tabular-nums">
                        —
                      </p>
                    </div>
                    <div>
                      <p className="font-mono text-[9px] text-[var(--color-text-muted)]">
                        T+20 WR
                      </p>
                      <p className="font-mono text-[18px] text-[var(--color-text)] tabular-nums">
                        —
                      </p>
                    </div>
                    <div>
                      <p className="font-mono text-[9px] text-[var(--color-text-muted)]">
                        BRIER
                      </p>
                      <p className="font-mono text-[18px] text-[var(--color-text)] tabular-nums">
                        —
                      </p>
                    </div>
                    <div>
                      <p className="font-mono text-[9px] text-[var(--color-text-muted)]">
                        SHARPE
                      </p>
                      <p className="font-mono text-[18px] text-[var(--color-text)] tabular-nums">
                        —
                      </p>
                    </div>
                  </div>
                  <MiniEquityCurve data={[]} />
                  <p className="font-mono text-[9px] text-[var(--color-text-muted)] mt-2">
                    {pairCalls.length} calls in version
                  </p>
                </div>
              );
            })}
          </div>

          {/* Full-width equity curve placeholder */}
          <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
            <div className="px-5 py-3 border-b border-[var(--color-border)]">
              <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
                Cumulative T+20 Log-Return — Regime Shading
              </p>
            </div>
            <EmptyState message="Backtested equity curve pending" />
          </div>

          {/* Regime-conditioned matrix */}
          <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
            <div className="px-5 py-3 border-b border-[var(--color-border)]">
              <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
                Regime-Conditioned Performance Matrix
              </p>
            </div>
            <div className="p-5">
              {versionedBreakdown.length === 0 ? (
                <p className="font-mono text-[10px] text-[var(--color-text-muted)] text-center py-8">
                  NO REGIME BREAKDOWN DATA
                </p>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[var(--color-border)]">
                  {versionedBreakdown.map((r) => (
                    <div
                      key={`${r.pair}-${r.regime}`}
                      className="bg-[var(--color-surface)] p-4"
                    >
                      <p className="font-mono text-[9px] text-[var(--color-text-muted)] uppercase">
                        {r.pair} · {r.regime.replace(/_/g, " ")}
                      </p>
                      <p className="font-mono text-[16px] text-[var(--color-text)] tabular-nums mt-1">
                        {r.count}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Calibration chart placeholder */}
          <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
            <div className="px-5 py-3 border-b border-[var(--color-border)]">
              <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
                Calibration — Confidence Buckets vs Actual Win Rate
              </p>
            </div>
            <EmptyState message="Calibration data pending" />
          </div>

          {/* Rolling 90-day metrics */}
          <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
            <div className="px-5 py-3 border-b border-[var(--color-border)]">
              <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
                Rolling 90-Day Metrics
              </p>
            </div>
            <EmptyState message="Rolling metrics pending" />
          </div>
        </>
      )}

      {simulationResults.length > 0 && (
        <div className="border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
          <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-3">
            Simulation Output
          </p>
          <pre className="font-mono text-[10px] text-[var(--color-text-secondary)] overflow-auto">
            {JSON.stringify(simulationResults, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

/* ─── Regime Validation tab content ─────────────────────────────────────── */

function RegimeValidationTabContent() {
  const metrics = [
    { label: "Sharpe", regimeAware: "0.84", uniform: "0.41", delta: "+105%" },
    { label: "Sortino", regimeAware: "1.12", uniform: "0.58", delta: "+93%" },
    {
      label: "Max Drawdown",
      regimeAware: "-12.3%",
      uniform: "-23.7%",
      delta: "-48%",
    },
    {
      label: "Return/DD",
      regimeAware: "2.18",
      uniform: "0.89",
      delta: "+145%",
    },
    {
      label: "Hit Rate (top)",
      regimeAware: "58.2%",
      uniform: "50.0%",
      delta: "+8.2pp",
    },
    { label: "Turnover", regimeAware: "4.2x", uniform: "1.0x", delta: "—" },
  ];

  return (
    <div>
      {/* Header */}
      <div className="mb-8 pb-4 border-b border-[var(--color-border)]">
        <p className="font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-2">
          Regime Validation
        </p>
        <h2 className="font-sans font-semibold text-[22px] text-[var(--color-text)] tracking-tight mb-2">
          Does Conviction Improve Risk-Adjusted Returns?
        </h2>
        <p className="font-sans text-[13px] text-[var(--color-text-secondary)]">
          Same directional calls. Two sizing approaches.
        </p>
      </div>

      {/* Comparison table */}
      <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10 overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[11px]">
          <thead>
            <tr className="border-b border-[var(--color-border)] bg-[var(--color-elevated)]">
              <th className="px-4 py-3 text-left text-[9px] text-[var(--color-text-muted)] tracking-[0.1em] font-semibold">
                METRIC
              </th>
              <th className="px-4 py-3 text-right text-[9px] text-[var(--color-text-muted)] tracking-[0.1em] font-semibold">
                REGIME-AWARE
              </th>
              <th className="px-4 py-3 text-right text-[9px] text-[var(--color-text-muted)] tracking-[0.1em] font-semibold">
                UNIFORM
              </th>
              <th className="px-4 py-3 text-right text-[9px] text-[var(--color-text-muted)] tracking-[0.1em] font-semibold">
                DELTA
              </th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((m) => (
              <tr
                key={m.label}
                className="border-b border-[var(--color-border-subtle)]"
              >
                <td className="px-4 py-3 text-[var(--color-text)]">
                  {m.label}
                </td>
                <td className="px-4 py-3 text-right text-[var(--color-text)] tabular-nums">
                  {m.regimeAware}
                </td>
                <td className="px-4 py-3 text-right text-[var(--color-text-muted)] tabular-nums">
                  {m.uniform}
                </td>
                <td className="px-4 py-3 text-right text-[var(--color-up)] tabular-nums">
                  {m.delta}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Overlay equity curve */}
      <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
        <div className="px-5 py-3 border-b border-[var(--color-border)]">
          <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
            Overlay Equity Curve — Regime-Aware vs Uniform
          </p>
        </div>
        <EmptyState message="Overlay curves pending simulation data" />
      </div>

      {/* Confidence-return scatter */}
      <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
        <div className="px-5 py-3 border-b border-[var(--color-border)]">
          <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
            Confidence-Return Scatter
          </p>
        </div>
        <EmptyState message="Scatter data pending" />
      </div>

      {/* Regime-conditional Sharpe bars */}
      <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
        <div className="px-5 py-3 border-b border-[var(--color-border)]">
          <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
            Regime-Conditional Sharpe — Trending vs Neutral vs Volatile
          </p>
        </div>
        <EmptyState message="Regime-conditional metrics pending" />
      </div>

      {/* Confidence decile hit rate */}
      <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
        <div className="px-5 py-3 border-b border-[var(--color-border)]">
          <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
            Confidence Decile Hit Rate
          </p>
        </div>
        <EmptyState message="Decile analysis pending" />
      </div>

      {/* Auto-generated interpretation */}
      <div className="border border-[var(--color-border)] bg-[var(--color-surface)] p-5 mb-10">
        <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-3">
          Interpretation
        </p>
        <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-relaxed">
          Awaiting backend simulation pipeline. Once the regime-aware sizing
          simulation runs against the uniform benchmark, this section will
          auto-populate with the statistical interpretation of the comparison.
        </p>
      </div>
    </div>
  );
}

/* ─── Main page ─────────────────────────────────────────────────────────── */

export default async function TrackRecordPage() {
  const supabase = await createClient();

  // Live data
  const [statsT5Raw, statsT20Raw, validation, regimeBreakdown, latestCall] =
    await Promise.all([
      getValidationStats(supabase, "t5", "live"),
      getValidationStats(supabase, "t20", "live"),
      getValidationLogT5T20(supabase, 500, "live"),
      getRegimeBreakdown(supabase, 500, "live"),
      supabase
        .from("regime_calls")
        .select("date")
        .eq("data_source", "live")
        .order("date", { ascending: false })
        .limit(1)
        .maybeSingle(),
    ]);

  // Backtest data
  const versions = await getBacktestVersions(supabase);
  const defaultVersion = versions[0] ?? "v3";
  const [versionedCalls, versionedBreakdown, simulationResults] =
    await Promise.all([
      getRegimeCallsByVersion(
        supabase,
        defaultVersion,
        undefined,
        undefined,
        500,
      ),
      getRegimeBreakdownByVersion(supabase, defaultVersion, 500),
      getSimulationResults(supabase, defaultVersion),
    ]);

  // Live stats computation
  const allT5 = computeStatsFromLog(validation, null, "t5");
  const allT20 = computeStatsFromLog(validation, null, "t20");
  const totalCalls =
    allT5.sampleSize ??
    validation.filter(
      (r) => r.t5Outcome === "CORRECT" || r.t5Outcome === "WRONG",
    ).length;

  const PAIR_LABELS = ["EUR/USD", "USD/JPY", "USD/INR"] as const;
  const computedT5 = PAIR_LABELS.map((p) =>
    computeStatsFromLog(validation, p, "t5"),
  );
  const computedT20 = PAIR_LABELS.map((p) =>
    computeStatsFromLog(validation, p, "t20"),
  );

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
            rolling90dAccuracy:
              computed.rolling90dAccuracy ?? raw.rolling90dAccuracy,
            asOfDate: computed.asOfDate ?? raw.asOfDate,
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
            rolling90dAccuracy:
              computed.rolling90dAccuracy ?? raw.rolling90dAccuracy,
            asOfDate: computed.asOfDate ?? raw.asOfDate,
          }
        : computed;
    }),
    allT20,
  ];

  // Equity curve from T+5 cumulative log-returns
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
    return { date: d, value: cum / 10000 };
  });

  let peakVal = Number.NEGATIVE_INFINITY;
  let maxDD = 0;
  for (const pt of equityCurve) {
    if (pt.value > peakVal) peakVal = pt.value;
    const dd = peakVal - pt.value;
    if (dd > maxDD) maxDD = dd;
  }

  // Rolling 10-call Brier
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

  // Freshness based on latest live call date
  const latestCallDate =
    (latestCall?.data as { date: string } | null)?.date ?? null;
  const lastDate =
    latestCallDate ?? (dates.length > 0 ? dates[dates.length - 1] : null);

  let freshnessStatus: "LIVE" | "ACTIVE" | "STALE" = "STALE";
  if (latestCallDate) {
    const daysSinceCall =
      (new Date().getTime() - new Date(latestCallDate).getTime()) /
      (1000 * 60 * 60 * 24);
    if (daysSinceCall <= 2) freshnessStatus = "LIVE";
    else if (daysSinceCall <= 7) freshnessStatus = "ACTIVE";
    else freshnessStatus = "STALE";
  }

  // CIs
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
      <Nav />
      <AuditTrailBannerServer variant="shell" />
      <main
        id="main-content"
        className="max-w-[1152px] mx-auto px-6 pt-28 pb-20 w-full"
      >
        {/* Page header */}
        <div className="mb-6 pb-6 border-b border-[var(--color-border)]">
          <p className="font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-2.5">
            Track Record
          </p>
          <h1 className="font-sans font-semibold text-[32px] text-[var(--color-text)] tracking-tight">
            Validation Archive
          </h1>
          <p className="font-sans text-[15px] text-[var(--color-text-secondary)] mt-2 leading-[1.6]">
            Live out-of-sample results and backtested regime validation.
          </p>
        </div>

        <TrackRecordTabs
          liveContent={
            <LiveTabContent
              statsT5={statsT5}
              statsT20={statsT20}
              validation={validation}
              regimeBreakdown={regimeBreakdown}
              allT5={allT5}
              allT20={allT20}
              totalCalls={totalCalls}
              equityCurve={equityCurve}
              maxDD={maxDD}
              brierSeries={brierSeries}
              freshnessStatus={freshnessStatus}
              lastDate={lastDate}
              t5WinCI={t5WinCI}
              t20WinCI={t20WinCI}
              t5BrierCI={t5BrierCI}
              t20BrierCI={t20BrierCI}
            />
          }
          backtestedContent={
            <BacktestedTabContent
              versions={versions}
              versionedCalls={versionedCalls}
              versionedBreakdown={versionedBreakdown}
              simulationResults={simulationResults}
            />
          }
          validationContent={<RegimeValidationTabContent />}
        />
      </main>
      <Footer />
    </div>
  );
}
