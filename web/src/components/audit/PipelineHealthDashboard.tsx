"use client";

import { useState } from "react";
import type { PipelineDayHealth, AccuracyAlert } from "@/lib/supabase/queries";

const STATUS_COLORS: Record<
  PipelineDayHealth["status"],
  { dot: string; bg: string; border: string; text: string; label: string }
> = {
  HEALTHY: {
    dot: "bg-emerald-400",
    bg: "bg-emerald-400/5",
    border: "border-emerald-400/30",
    text: "text-emerald-400",
    label: "HEALTHY",
  },
  DEGRADED: {
    dot: "bg-amber-400",
    bg: "bg-amber-400/5",
    border: "border-amber-400/30",
    text: "text-amber-400",
    label: "DEGRADED",
  },
  FAILED: {
    dot: "bg-red-400",
    bg: "bg-red-400/5",
    border: "border-red-400/30",
    text: "text-red-400",
    label: "FAILED",
  },
  UNKNOWN: {
    dot: "bg-gray-500",
    bg: "bg-gray-500/5",
    border: "border-gray-500/30",
    text: "text-gray-500",
    label: "UNKNOWN",
  },
};

function fmtDate(dateStr: string) {
  const m = dateStr.slice(5, 7);
  const d = dateStr.slice(8, 10);
  return `${m}-${d}`;
}

function DQSSparkline({ data }: { data: { date: string; value: number | null }[] }) {
  const valid = data.filter((d) => d.value != null);
  if (valid.length < 2) {
    return (
      <div className="h-16 w-full flex items-center justify-center border border-[var(--color-border)] bg-[var(--color-surface)]">
        <span className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-wider">
          NO DQS DATA
        </span>
      </div>
    );
  }

  const W = 300;
  const H = 64;
  const padL = 4;
  const padR = 4;
  const padT = 4;
  const padB = 4;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;

  const values = valid.map((d) => d.value as number);
  let minV = Math.min(...values);
  let maxV = Math.max(...values);
  if (minV === maxV) {
    minV -= 0.1;
    maxV += 0.1;
  }
  const range = maxV - minV || 1;

  const pts = valid.map((d, i) => {
    const x = padL + (i / (valid.length - 1)) * chartW;
    const y = padT + chartH - ((d.value! - minV) / range) * chartH;
    return { x, y, date: d.date };
  });

  const lineD = pts
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(" ");

  const areaD = `M ${pts[0].x.toFixed(1)} ${padT + chartH} ${pts.map((p) => `L ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ")} L ${pts[pts.length - 1].x.toFixed(1)} ${padT + chartH} Z`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="w-full h-16 block">
      <title>DQS Trend</title>
      <rect width={W} height={H} fill="var(--color-surface)" />
      <path d={areaD} fill="rgba(52,211,153,0.08)" />
      <path
        d={lineD}
        fill="none"
        stroke="#34d399"
        strokeWidth={1.5}
        vectorEffect="non-scaling-stroke"
      />
      {pts.map((p, i) => (
        <circle
          key={p.date}
          cx={p.x}
          cy={p.y}
          r={2}
          fill="#34d399"
          opacity={i === pts.length - 1 ? 1 : 0.5}
        />
      ))}
    </svg>
  );
}

export function PipelineHealthDashboard({
  health,
  alerts,
}: {
  health: PipelineDayHealth[];
  alerts: AccuracyAlert[];
}) {
  const [selectedDate, setSelectedDate] = useState<string>(health[0]?.date ?? "");
  const selectedDay = health.find((d) => d.date === selectedDate) ?? health[0];

  const dqsData = health
    .slice()
    .reverse()
    .map((d) => ({ date: d.date, value: d.dqs }));

  return (
    <div className="space-y-6">
      {/* Accuracy Alert Banner */}
      {alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.map((alert) => (
            <div
              key={alert.pair}
              className={`border px-4 py-3 ${
                alert.severity === "critical"
                  ? "border-red-400/30 bg-red-400/5"
                  : "border-amber-400/30 bg-amber-400/5"
              }`}
            >
              <div className="flex items-center gap-2 flex-wrap">
                <span
                  className={`inline-block h-2 w-2 rounded-full ${
                    alert.severity === "critical" ? "bg-red-400" : "bg-amber-400"
                  }`}
                />
                <span className="font-mono text-[10px] tracking-wider uppercase text-[var(--color-text)]">
                  {alert.severity === "critical" ? "Accuracy Alert" : "Warning"}
                </span>
                <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
                  —
                </span>
                <span className="font-mono text-[10px] text-[var(--color-text-secondary)]">
                  {alert.pair} rolling 90D accuracy is{" "}
                  <span className="tabular-nums">
                    {(alert.accuracy * 100).toFixed(1)}%
                  </span>
                  {alert.severity === "critical" ? (
                    <span className="text-red-400">
                      {" "}
                      (&lt; {(alert.threshold * 100).toFixed(0)}%)
                    </span>
                  ) : (
                    <span className="text-amber-400">
                      {" "}
                      (&lt; {(alert.threshold * 100).toFixed(0)}%)
                    </span>
                  )}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 14-Day Status Grid */}
      <div>
        <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-3">
          Last 14 Days
        </p>
        <div className="flex flex-wrap gap-2">
          {health.map((day) => {
            const colors = STATUS_COLORS[day.status];
            const isSelected = day.date === selectedDate;
            return (
              <button
                key={day.date}
                type="button"
                onClick={() => setSelectedDate(day.date)}
                className={`relative flex flex-col items-center justify-center gap-1.5 border px-2 py-2 min-w-[52px] transition-colors cursor-pointer ${
                  isSelected
                    ? `${colors.border} ${colors.bg} ring-1 ring-inset ${colors.text.replace("text-", "ring-")}`
                    : "border-[var(--color-border)] bg-[var(--color-surface)] hover:border-[var(--color-border-bright)]"
                }`}
                title={`${day.date} — ${day.status}`}
              >
                <span
                  className={`h-2 w-2 rounded-full ${colors.dot} ${day.status === "HEALTHY" ? "animate-gentle-pulse" : ""}`}
                />
                <span className="font-mono text-[9px] text-[var(--color-text-muted)] tabular-nums">
                  {fmtDate(day.date)}
                </span>
                {/* Tooltip-like overlay on hover */}
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-10">
                  <div className="border border-[var(--color-border)] bg-[var(--color-void)] px-2 py-1 whitespace-nowrap">
                    <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
                      {day.regimeCallsCount} calls · DQS {day.dqs != null ? (day.dqs * 100).toFixed(0) : "—"}%
                    </span>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* DQS Sparkline */}
      <div className="border border-[var(--color-border)] bg-[var(--color-surface)]">
        <div className="px-4 py-2 border-b border-[var(--color-border)] flex items-center justify-between">
          <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
            DQS Trend — 14D
          </p>
          <span className="font-mono text-[9px] text-[var(--color-text-muted)] tabular-nums">
            {selectedDay?.dqs != null
              ? `Latest: ${(selectedDay.dqs * 100).toFixed(0)}%`
              : "Latest: —"}
          </span>
        </div>
        <DQSSparkline data={dqsData} />
      </div>

      {/* Current Day Detail Panel */}
      {selectedDay && (
        <div className="border border-[var(--color-border)] bg-[var(--color-surface)]">
          <div className="px-4 py-3 border-b border-[var(--color-border)] flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <span
                className={`inline-flex items-center gap-1.5 border px-2 py-0.5 font-mono text-[10px] tracking-wider uppercase ${STATUS_COLORS[selectedDay.status].border} ${STATUS_COLORS[selectedDay.status].bg} ${STATUS_COLORS[selectedDay.status].text}`}
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full ${STATUS_COLORS[selectedDay.status].dot}`}
                />
                {selectedDay.status}
              </span>
              <span className="font-mono text-[10px] text-[var(--color-text-muted)] tabular-nums">
                {selectedDay.date}
              </span>
            </div>
            <div className="flex items-center gap-4">
              <span className="font-mono text-[9px] text-[var(--color-text-muted)] tabular-nums">
                Calls: {selectedDay.regimeCallsCount}
              </span>
              {selectedDay.dqs != null && (
                <span className="font-mono text-[9px] text-[var(--color-text-muted)] tabular-nums">
                  DQS: {(selectedDay.dqs * 100).toFixed(0)}%
                </span>
              )}
            </div>
          </div>

          <div className="p-4 space-y-4">
            {/* Steps */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <p className="font-mono text-[9px] tracking-wider text-[var(--color-text-muted)] uppercase mb-2">
                  Steps Completed
                </p>
                {selectedDay.stepsCompleted.length > 0 ? (
                  <ul className="space-y-1">
                    {selectedDay.stepsCompleted.map((step) => (
                      <li
                        key={step}
                        className="flex items-center gap-2 font-mono text-[10px] text-emerald-400"
                      >
                        <svg
                          width="12"
                          height="12"
                          viewBox="0 0 12 12"
                          fill="none"
                          className="shrink-0"
                        >
                          <path
                            d="M2 6L5 9L10 3"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                        {step}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="font-mono text-[10px] text-[var(--color-text-dim)]">
                    None
                  </p>
                )}
              </div>
              <div>
                <p className="font-mono text-[9px] tracking-wider text-[var(--color-text-muted)] uppercase mb-2">
                  Steps Failed
                </p>
                {selectedDay.stepsFailed.length > 0 ? (
                  <ul className="space-y-1">
                    {selectedDay.stepsFailed.map((step) => (
                      <li
                        key={step}
                        className="flex items-center gap-2 font-mono text-[10px] text-red-400"
                      >
                        <svg
                          width="12"
                          height="12"
                          viewBox="0 0 12 12"
                          fill="none"
                          className="shrink-0"
                        >
                          <path
                            d="M3 3L9 9M9 3L3 9"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                          />
                        </svg>
                        {step}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="font-mono text-[10px] text-[var(--color-text-dim)]">
                    None
                  </p>
                )}
              </div>
            </div>

            {/* DQS Progress Bar */}
            {selectedDay.dqs != null && (
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-mono text-[9px] tracking-wider text-[var(--color-text-muted)] uppercase">
                    Data Quality Score
                  </span>
                  <span className="font-mono text-[10px] text-[var(--color-text-secondary)] tabular-nums">
                    {(selectedDay.dqs * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-1.5 w-full bg-[var(--color-sunken)] overflow-hidden">
                  <div
                    className="h-full bg-emerald-400 transition-all"
                    style={{ width: `${Math.min(100, Math.max(0, selectedDay.dqs * 100))}%` }}
                  />
                </div>
              </div>
            )}

            {/* Validation & AI Briefs */}
            <div className="flex flex-wrap gap-4">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[9px] tracking-wider text-[var(--color-text-muted)] uppercase">
                  Validation:
                </span>
                <span
                  className={`font-mono text-[10px] ${
                    selectedDay.validationComputed
                      ? "text-emerald-400"
                      : "text-red-400"
                  }`}
                >
                  {selectedDay.validationComputed ? "YES" : "NO"}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[9px] tracking-wider text-[var(--color-text-muted)] uppercase">
                  AI Briefs:
                </span>
                <span
                  className={`font-mono text-[10px] ${
                    selectedDay.aiBriefsGenerated
                      ? "text-emerald-400"
                      : "text-red-400"
                  }`}
                >
                  {selectedDay.aiBriefsGenerated ? "YES" : "NO"}
                </span>
              </div>
            </div>

            {/* Errors */}
            {selectedDay.errors.length > 0 && (
              <div className="border border-red-400/20 bg-red-400/5 p-3">
                <p className="font-mono text-[9px] tracking-wider text-red-400 uppercase mb-1.5">
                  Errors
                </p>
                <ul className="space-y-1">
                  {selectedDay.errors.map((err, i) => (
                    <li
                      key={i}
                      className="font-mono text-[10px] text-red-300 leading-relaxed"
                    >
                      {err}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
