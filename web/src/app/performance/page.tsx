import { ValidationTable } from "@/components/regime/ValidationTable";
import { Footer } from "@/components/shell/Footer";
import { Nav } from "@/components/shell/Nav";
import { PAIRS } from "@/lib/constants";
import { getValidationLog } from "@/lib/supabase/queries";
import type { ValidationRow } from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";
import Link from "next/link";

/* ─── helpers ───────────────────────────────────────────────────────────── */

function fmtPct(n: number, digits = 2) {
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(digits)}%`;
}

function hitColor(rate: number) {
  if (rate >= 60) return "var(--color-up)";
  if (rate >= 40) return "var(--color-warn)";
  return "var(--color-down)";
}

function retColor(n: number) {
  return n >= 0 ? "var(--color-up)" : "var(--color-down)";
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

  // running peak for drawdown shading
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

  // equity line
  const lineD = pts
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(" ");

  // area below equity line
  const areaD = `M ${pts[0].x.toFixed(1)} ${padT + chartH} ${pts.map((p) => `L ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ")} L ${pts[pts.length - 1].x.toFixed(1)} ${padT + chartH} Z`;

  // drawdown fill (between equity and peak)
  const ddD = `${lineD} ${pts
    .slice()
    .reverse()
    .map((p) => `L ${p.x.toFixed(1)} ${p.yPeak.toFixed(1)}`)
    .join(" ")} Z`;

  // y ticks
  const yTicks = [maxV, (minV + maxV) / 2, minV];

  // x labels (show ~5 evenly spaced)
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
      {/* background */}
      <rect width={W} height={H} fill="#000000" />

      {/* horizontal grid */}
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

      {/* area fill */}
      <path d={areaD} fill="rgba(214,211,209,0.08)" />

      {/* drawdown haze */}
      <path d={ddD} fill="rgba(184,122,122,0.06)" />

      {/* equity line */}
      <path
        d={lineD}
        fill="none"
        stroke="#d6d3d1"
        strokeWidth={2}
        vectorEffect="non-scaling-stroke"
      />

      {/* y-axis labels */}
      {yTicks.map((v, i) => {
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
            {fmtPct(v)}
          </text>
        );
      })}

      {/* x-axis labels */}
      {xLabels.map((p, i) => (
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

export default async function PerformancePage() {
  const supabase = await createClient();
  const validation = await getValidationLog(supabase, 500);

  const totalCalls = validation.length;
  const correct = validation.filter(
    (r: ValidationRow) => r.outcome === "correct",
  ).length;
  const accuracy = totalCalls > 0 ? (correct / totalCalls) * 100 : 0;
  const avgReturn =
    totalCalls > 0
      ? validation.reduce(
          (s: number, r: ValidationRow) => s + r.return_pct,
          0,
        ) / totalCalls
      : 0;
  const cumulativeReturn = validation.reduce(
    (s: number, r: ValidationRow) => s + r.return_pct,
    0,
  );

  // 7D accuracy
  const cut7 = new Date();
  cut7.setUTCDate(cut7.getUTCDate() - 7);
  const cut7Str = cut7.toISOString().slice(0, 10);
  const last7 = validation.filter((r: ValidationRow) => r.date >= cut7Str);
  const correct7 = last7.filter(
    (r: ValidationRow) => r.outcome === "correct",
  ).length;
  const accuracy7d = last7.length > 0 ? (correct7 / last7.length) * 100 : 0;

  // equity curve: sum daily returns, cumulative
  const sortedAsc = [...validation].sort((a, b) =>
    a.date.localeCompare(b.date),
  );
  const byDate = new Map<string, number>();
  for (const r of sortedAsc) {
    byDate.set(r.date, (byDate.get(r.date) ?? 0) + r.return_pct);
  }
  const dates = [...byDate.keys()].sort();
  let cum = 0;
  const equityCurve = dates.map((d) => {
    const daily = byDate.get(d);
    if (daily != null) cum += daily;
    return { date: d, value: cum };
  });

  // max drawdown from equity curve
  let peakVal = Number.NEGATIVE_INFINITY;
  let maxDD = 0;
  for (const pt of equityCurve) {
    if (pt.value > peakVal) peakVal = pt.value;
    const dd = peakVal - pt.value;
    if (dd > maxDD) maxDD = dd;
  }

  // hit rate by horizon (T+1 real; T+5 / T+20 not yet available)
  const hitRates = [
    {
      horizon: "T+1" as const,
      label: "next day",
      hits: correct,
      trials: totalCalls,
    },
    {
      horizon: "T+5" as const,
      label: "1 week",
      hits: 0,
      trials: 0,
      insufficient: true as const,
    },
    {
      horizon: "T+20" as const,
      label: "1 month",
      hits: 0,
      trials: 0,
      insufficient: true as const,
    },
  ];

  // per-pair accuracy
  const pairStats = PAIRS.map((p) => {
    const rows = validation.filter((r: ValidationRow) => r.pair === p.display);
    const pCorrect = rows.filter(
      (r: ValidationRow) => r.outcome === "correct",
    ).length;
    const pAcc = rows.length ? (pCorrect / rows.length) * 100 : 0;
    return { ...p, rows, correct: pCorrect, accuracy: pAcc };
  });

  // regime breakdown
  const regimeMap = new Map<string, ValidationRow[]>();
  for (const r of validation) {
    const arr = regimeMap.get(r.call) ?? [];
    arr.push(r);
    regimeMap.set(r.call, arr);
  }
  const regimes = [...regimeMap.entries()]
    .map(([regime, rows]) => {
      const rCorrect = rows.filter((r) => r.outcome === "correct").length;
      const rTotal = rows.length;
      const rAvg =
        rTotal > 0 ? rows.reduce((s, r) => s + r.return_pct, 0) / rTotal : 0;
      const rMin = rTotal > 0 ? Math.min(...rows.map((r) => r.return_pct)) : 0;

      // current streak for this regime (chronological)
      const sortedRows = [...rows].sort((a, b) => a.date.localeCompare(b.date));
      let streak: { type: "W" | "L"; count: number } | null = null;
      if (sortedRows.length > 0) {
        const last = sortedRows[sortedRows.length - 1];
        const type = last.outcome === "correct" ? "W" : "L";
        let count = 0;
        for (let i = sortedRows.length - 1; i >= 0; i--) {
          const expected = type === "W" ? "correct" : "incorrect";
          if (sortedRows[i].outcome === expected) count++;
          else break;
        }
        streak = { type, count };
      }

      return {
        regime,
        calls: rTotal,
        hits: rCorrect,
        hitRate: rTotal > 0 ? (rCorrect / rTotal) * 100 : 0,
        avgReturn: rAvg,
        maxDrawdown: rMin,
        streak,
      };
    })
    .sort((a, b) => b.calls - a.calls);

  // monthly breakdown (newest first)
  const monthMap = new Map<string, ValidationRow[]>();
  for (const r of validation) {
    const m = r.date.slice(0, 7);
    const arr = monthMap.get(m) ?? [];
    arr.push(r);
    monthMap.set(m, arr);
  }
  const monthsAsc = [...monthMap.keys()].sort();
  let runningCum = 0;
  const monthlyAsc = monthsAsc.map((m) => {
    const rows = monthMap.get(m) ?? [];
    const mCorrect = rows.filter((r) => r.outcome === "correct").length;
    const mTotal = rows.length;
    const mAvg =
      mTotal > 0 ? rows.reduce((s, r) => s + r.return_pct, 0) / mTotal : 0;
    const mSum = rows.reduce((s, r) => s + r.return_pct, 0);
    runningCum += mSum;
    return {
      month: m,
      calls: mTotal,
      hits: mCorrect,
      misses: mTotal - mCorrect,
      hitRate: mTotal > 0 ? (mCorrect / mTotal) * 100 : 0,
      avgReturn: mAvg,
      monthReturn: mSum,
      cumulativeReturn: runningCum,
    };
  });
  const monthly = [...monthlyAsc].reverse();

  // freshness
  const lastDate = dates.length > 0 ? dates[dates.length - 1] : null;
  const isStale = lastDate
    ? new Date().getTime() - new Date(lastDate).getTime() > 24 * 60 * 60 * 1000
    : true;

  return (
    <div className="min-h-screen bg-[var(--color-void)]">
      <Nav />
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
                Next-day directional validation. Updated daily after market
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

        {/* ── Equity Curve ───────────────────────────────────────────────── */}
        <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
          <div className="px-5 py-3 border-b border-[var(--color-border)] flex items-center justify-between">
            <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
              Equity Curve — Cumulative Directional Return
            </p>
            <div className="flex items-center gap-4">
              <span className="font-mono text-[10px] text-[var(--color-text-muted)] tabular-nums">
                Max DD:{" "}
                <span style={{ color: "var(--color-down)" }}>
                  {fmtPct(-maxDD)}
                </span>
              </span>
            </div>
          </div>
          <EquityCurveSVG data={equityCurve} />
        </div>

        {/* ── Metrics Strip ──────────────────────────────────────────────── */}
        <div
          className={`grid grid-cols-2 md:grid-cols-4 gap-px bg-[var(--color-border)] border border-[var(--color-border)] mb-10 ${isStale ? "opacity-50" : ""}`}
        >
          {[
            {
              label: "7D ACCURACY",
              value: `${accuracy7d.toFixed(1)}%`,
              sub: `${correct7}/${last7.length} correct`,
            },
            {
              label: "CUMULATIVE RETURN",
              value: fmtPct(cumulativeReturn),
              sub: "Since inception",
            },
            {
              label: "CALLS VALIDATED",
              value: `${totalCalls}`,
              sub: `${PAIRS.length} pairs`,
            },
            {
              label: "AVG NEXT-DAY RET",
              value: fmtPct(avgReturn),
              sub: "Per call directional",
            },
          ].map((m) => (
            <div key={m.label} className="bg-[var(--color-surface)] p-5 md:p-6">
              <p className="font-mono text-[9px] tracking-[0.12em] text-[var(--color-text-muted)] uppercase mb-2.5">
                {m.label}
              </p>
              <p className="font-mono text-[clamp(22px,3vw,28px)] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">
                {m.value}
              </p>
              <p className="font-mono text-[10px] text-[var(--color-text-muted)] mt-1.5 tabular-nums">
                {m.sub}
              </p>
            </div>
          ))}
        </div>

        {/* ── Hit Rate by Horizon ────────────────────────────────────────── */}
        <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
          <div className="px-5 py-3 border-b border-[var(--color-border)]">
            <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
              Hit Rate by Horizon
            </p>
          </div>
          <div className="px-5 py-5 space-y-5">
            {hitRates.map((h) => {
              const rate = h.trials > 0 ? (h.hits / h.trials) * 100 : 0;
              return (
                <div
                  key={h.horizon}
                  className="flex items-center gap-4 flex-wrap"
                >
                  <div className="w-[80px]">
                    <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-secondary)] uppercase">
                      {h.horizon}
                    </p>
                    <p className="font-mono text-[9px] text-[var(--color-text-muted)]">
                      {h.label}
                    </p>
                  </div>
                  <div className="flex-1 min-w-[120px] max-w-[50%] bg-[var(--color-panel)] h-[4px] overflow-hidden">
                    <div
                      className="h-full transition-all duration-700 ease-out"
                      style={{
                        width: `${h.trials > 0 ? rate : 0}%`,
                        backgroundColor: hitColor(rate),
                        transitionTimingFunction:
                          "cubic-bezier(0.16, 1, 0.3, 1)",
                      }}
                    />
                  </div>
                  <div className="w-[100px] text-right">
                    <p className="font-mono text-[13px] tabular-nums text-[var(--color-text)]">
                      {"insufficient" in h && h.insufficient
                        ? "—"
                        : h.trials > 0
                          ? `${rate.toFixed(1)}%`
                          : "—"}
                    </p>
                    <p className="font-mono text-[9px] text-[var(--color-text-muted)] tabular-nums">
                      {"insufficient" in h && h.insufficient
                        ? "insufficient data"
                        : h.trials > 0
                          ? `${h.hits}/${h.trials}`
                          : "0/0"}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Per-pair Accuracy ──────────────────────────────────────────── */}
        <div className="border border-[var(--color-border)] mb-10 bg-[var(--color-surface)]">
          <div className="px-5 py-3 border-b border-[var(--color-border)]">
            <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
              Rolling 7-Day Accuracy
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-px bg-[var(--color-border-subtle)]">
            {pairStats.map((p) => (
              <div
                key={p.label}
                className="px-5 py-5 bg-[var(--color-surface)]"
              >
                <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-secondary)] uppercase font-medium mb-2">
                  {p.display}
                </p>
                <p className="font-mono text-[26px] font-medium text-[var(--color-text)] tracking-tight tabular-nums">
                  {p.rows.length ? `${p.accuracy.toFixed(0)}%` : "—"}
                </p>
                <p className="font-mono text-[10px] text-[var(--color-text-muted)] mt-0.5 tabular-nums">
                  {p.rows.length} calls
                </p>
                <div className="mt-3 bg-[var(--color-panel)] h-[2px] overflow-hidden">
                  <div
                    className="h-full bg-[var(--color-text-muted)] transition-all duration-700 ease-out"
                    style={{
                      width: `${p.rows.length ? p.accuracy : 0}%`,
                      transitionTimingFunction: "cubic-bezier(0.16, 1, 0.3, 1)",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── Regime Performance Breakdown ───────────────────────────────── */}
        <div className="border border-[var(--color-border)] mb-10 bg-[var(--color-surface)] overflow-hidden">
          <div className="px-5 py-3 border-b border-[var(--color-border)]">
            <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
              Regime Performance
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse font-mono text-[11px]">
              <thead>
                <tr className="border-b border-[var(--color-border)] bg-[var(--color-elevated)]">
                  {[
                    "REGIME",
                    "CALLS",
                    "HIT %",
                    "AVG RET",
                    "MAX DD",
                    "STREAK",
                  ].map((h) => (
                    <th
                      key={h}
                      scope="col"
                      className="px-4 py-2.5 text-left text-[9px] text-[var(--color-text-muted)] tracking-[0.15em] font-semibold uppercase whitespace-nowrap"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {regimes.map((r, i) => (
                  <tr
                    key={r.regime}
                    className={`border-b border-[var(--color-border-subtle)] last:border-b-0 ${i % 2 === 1 ? "bg-[var(--color-elevated)]" : "bg-[var(--color-surface)]"} hover:bg-[var(--color-elevated)] transition-colors`}
                  >
                    <td className="px-4 py-2.5 text-[var(--color-text-secondary)] whitespace-nowrap">
                      {r.regime}
                    </td>
                    <td className="px-4 py-2.5 text-[var(--color-text)] tabular-nums">
                      {r.calls}
                    </td>
                    <td
                      className="px-4 py-2.5 font-bold tabular-nums"
                      style={{ color: hitColor(r.hitRate) }}
                    >
                      {r.calls > 0 ? `${r.hitRate.toFixed(0)}%` : "—"}
                    </td>
                    <td
                      className="px-4 py-2.5 font-bold tabular-nums"
                      style={{ color: retColor(r.avgReturn) }}
                    >
                      {r.calls > 0 ? fmtPct(r.avgReturn) : "—"}
                    </td>
                    <td
                      className="px-4 py-2.5 font-bold tabular-nums"
                      style={{ color: "var(--color-down)" }}
                    >
                      {r.calls > 0 ? fmtPct(r.maxDrawdown) : "—"}
                    </td>
                    <td className="px-4 py-2.5 tabular-nums">
                      {r.streak ? (
                        <span
                          style={{
                            color:
                              r.streak.type === "W"
                                ? "var(--color-up)"
                                : "var(--color-down)",
                          }}
                        >
                          {r.streak.type}
                          {r.streak.count}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                ))}
                {regimes.length === 0 && (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-4 py-6 text-center text-[var(--color-text-muted)]"
                    >
                      No regime data available
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── Monthly Performance ────────────────────────────────────────── */}
        <div className="border border-[var(--color-border)] mb-10 bg-[var(--color-surface)] overflow-hidden">
          <div className="px-5 py-3 border-b border-[var(--color-border)]">
            <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
              Monthly Breakdown
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse font-mono text-[11px]">
              <thead>
                <tr className="border-b border-[var(--color-border)] bg-[var(--color-elevated)]">
                  {[
                    "MONTH",
                    "CALLS",
                    "HITS",
                    "MISS",
                    "HIT %",
                    "AVG RET",
                    "CUM RET",
                  ].map((h) => (
                    <th
                      key={h}
                      scope="col"
                      className="px-4 py-2.5 text-left text-[9px] text-[var(--color-text-muted)] tracking-[0.15em] font-semibold uppercase whitespace-nowrap"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {monthly.map((m, i) => (
                  <tr
                    key={m.month}
                    className={`border-b border-[var(--color-border-subtle)] last:border-b-0 ${i % 2 === 1 ? "bg-[var(--color-elevated)]" : "bg-[var(--color-surface)]"} hover:bg-[var(--color-elevated)] transition-colors`}
                  >
                    <td className="px-4 py-2.5 text-[var(--color-text-secondary)] tabular-nums whitespace-nowrap">
                      {m.month}
                    </td>
                    <td className="px-4 py-2.5 text-[var(--color-text)] tabular-nums">
                      {m.calls}
                    </td>
                    <td className="px-4 py-2.5 text-[var(--color-up)] tabular-nums">
                      {m.hits}
                    </td>
                    <td className="px-4 py-2.5 text-[var(--color-down)] tabular-nums">
                      {m.misses}
                    </td>
                    <td
                      className="px-4 py-2.5 font-bold tabular-nums"
                      style={{ color: hitColor(m.hitRate) }}
                    >
                      {m.calls > 0 ? `${m.hitRate.toFixed(0)}%` : "—"}
                    </td>
                    <td
                      className="px-4 py-2.5 font-bold tabular-nums"
                      style={{ color: retColor(m.avgReturn) }}
                    >
                      {m.calls > 0 ? fmtPct(m.avgReturn) : "—"}
                    </td>
                    <td
                      className="px-4 py-2.5 font-bold tabular-nums"
                      style={{ color: retColor(m.cumulativeReturn) }}
                    >
                      {fmtPct(m.cumulativeReturn)}
                    </td>
                  </tr>
                ))}
                {monthly.length === 0 && (
                  <tr>
                    <td
                      colSpan={7}
                      className="px-4 py-6 text-center text-[var(--color-text-muted)]"
                    >
                      No monthly data available
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── Validation Log ─────────────────────────────────────────────── */}
        <div className="mb-10">
          <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-4">
            Validation Log — All Calls
          </p>
          <ValidationTable rows={validation} tone="dark" />
        </div>

        {/* ── Disclaimer ─────────────────────────────────────────────────── */}
        <p className="font-mono text-[10px] text-[var(--color-text-muted)] tracking-wider leading-relaxed pt-5 mt-5 border-t border-[var(--color-border)]">
          NEXT-DAY DIRECTIONAL OUTCOME. RETURN % IS NEXT-DAY CLOSE-TO-CLOSE SPOT
          MOVE IN DIRECTION OF CALL. RESEARCH ONLY — NOT INVESTMENT ADVICE.
        </p>
      </main>
      <Footer />
    </div>
  );
}
