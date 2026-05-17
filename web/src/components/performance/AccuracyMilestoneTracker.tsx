"use client";

import { useMemo } from "react";

interface HistoryPoint {
  date: string;
  accuracy: number;
}

interface AccuracyMilestoneTrackerProps {
  currentAccuracy: number;
  history: HistoryPoint[];
  daysAboveGate: number;
  currentStreak: number;
  bestWindowAccuracy: number;
}

const GATE = 0.55;
const MAX_BAR = 0.6;

function StatusBadge({ accuracy }: { accuracy: number }) {
  if (accuracy >= GATE) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-none border border-emerald-400/30 bg-emerald-400/10 px-2 py-1 font-mono text-[10px] tracking-wider text-emerald-400">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
        ABOVE GATE
      </span>
    );
  }
  if (accuracy >= 0.45) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-none border border-amber-400/30 bg-amber-400/10 px-2 py-1 font-mono text-[10px] tracking-wider text-amber-400">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
        APPROACHING
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-none border border-red-400/30 bg-red-400/10 px-2 py-1 font-mono text-[10px] tracking-wider text-red-400">
      <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
      BELOW BASELINE
    </span>
  );
}

function Sparkline({ data }: { data: HistoryPoint[] }) {
  const svgWidth = 300;
  const svgHeight = 60;
  const padding = 4;

  const points = useMemo(() => {
    if (data.length < 2) return "";
    const minAcc = Math.min(...data.map((d) => d.accuracy), GATE - 0.05);
    const maxAcc = Math.max(...data.map((d) => d.accuracy), GATE + 0.05);
    const range = maxAcc - minAcc || 0.01;

    return data
      .map((d, i) => {
        const x = padding + (i / (data.length - 1)) * (svgWidth - padding * 2);
        const y =
          svgHeight -
          padding -
          ((d.accuracy - minAcc) / range) * (svgHeight - padding * 2);
        return `${x},${y}`;
      })
      .join(" ");
  }, [data]);

  const gateY = useMemo(() => {
    if (data.length < 2) return svgHeight / 2;
    const minAcc = Math.min(...data.map((d) => d.accuracy), GATE - 0.05);
    const maxAcc = Math.max(...data.map((d) => d.accuracy), GATE + 0.05);
    const range = maxAcc - minAcc || 0.01;
    return (
      svgHeight -
      padding -
      ((GATE - minAcc) / range) * (svgHeight - padding * 2)
    );
  }, [data]);

  return (
    <svg
      width="100%"
      height={svgHeight}
      viewBox={`0 0 ${svgWidth} ${svgHeight}`}
      preserveAspectRatio="none"
      role="img"
      aria-label="Accuracy milestone tracker"
    >
      <title>Accuracy Milestone Tracker</title>
      {/* Gate line */}
      <line
        x1={padding}
        y1={gateY}
        x2={svgWidth - padding}
        y2={gateY}
        stroke="var(--terminal-success)"
        strokeWidth="0.5"
        strokeDasharray="4 2"
        opacity={0.5}
      />
      {/* Area under curve */}
      {points && (
        <polyline
          points={points}
          fill="none"
          stroke="var(--terminal-success)"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
    </svg>
  );
}

export function AccuracyMilestoneTracker({
  currentAccuracy,
  history,
  daysAboveGate,
  currentStreak,
  bestWindowAccuracy,
}: AccuracyMilestoneTrackerProps) {
  const pct = Math.round(currentAccuracy * 1000) / 10;
  const bestPct = Math.round(bestWindowAccuracy * 1000) / 10;
  const barPct = Math.min(currentAccuracy / MAX_BAR, 1);
  const gatePct = GATE / MAX_BAR;

  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-surface)] p-6 md:p-8">
      {/* Header */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <span className="block font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-2">
            EUR/USD 90-Day Accuracy
          </span>
          <div className="flex items-baseline gap-3">
            <span className="font-mono text-[clamp(36px,5vw,52px)] font-medium text-[var(--color-text)] tracking-tight tabular-nums leading-none">
              {pct.toFixed(1)}%
            </span>
            <StatusBadge accuracy={currentAccuracy} />
          </div>
        </div>
        <div className="text-right">
          <span className="block font-mono text-[9px] tracking-wider text-[var(--color-text-muted)] uppercase">
            Target
          </span>
          <span className="font-mono text-[18px] font-medium text-emerald-400 tabular-nums">
            55.0%
          </span>
          <span className="block font-mono text-[9px] text-[var(--color-text-dim)]">
            GBP/USD expansion gate
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mb-6">
        <div className="relative h-3 w-full bg-[var(--color-void)]">
          {/* Zone backgrounds */}
          <div className="absolute left-0 top-0 h-full w-[75%] bg-red-400/10" />
          <div className="absolute left-[75%] top-0 h-full w-[8.3%] bg-amber-400/10" />
          <div className="absolute left-[83.3%] top-0 h-full w-[16.7%] bg-emerald-400/10" />

          {/* Gate marker */}
          <div
            className="absolute top-[-4px] h-[20px] w-[1px] bg-emerald-400"
            style={{ left: `${gatePct * 100}%` }}
          >
            <span className="absolute left-1/2 top-[-16px] -translate-x-1/2 font-mono text-[8px] tracking-wider text-emerald-400">
              GATE
            </span>
          </div>

          {/* Current position */}
          <div
            className="absolute top-0 h-full bg-emerald-400 transition-all duration-1000"
            style={{ width: `${barPct * 100}%` }}
          />
        </div>
        {/* Milestone labels */}
        <div className="relative mt-2 h-4">
          {[
            { label: "45%", pct: 0.45 / MAX_BAR },
            { label: "50%", pct: 0.5 / MAX_BAR },
            { label: "55%", pct: GATE / MAX_BAR },
            { label: "60%", pct: 0.6 / MAX_BAR },
          ].map((m) => (
            <span
              key={m.label}
              className="absolute -translate-x-1/2 font-mono text-[8px] text-[var(--color-text-dim)]"
              style={{ left: `${m.pct * 100}%` }}
            >
              {m.label}
            </span>
          ))}
        </div>
      </div>

      {/* Sparkline + Stats */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-[1fr_200px]">
        <div>
          <span className="mb-2 block font-mono text-[9px] tracking-wider text-[var(--color-text-muted)] uppercase">
            30-Day History
          </span>
          <div className="border border-[var(--color-border)] bg-[var(--color-void)] p-3">
            <Sparkline data={history} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-px bg-[var(--color-border)] md:grid-cols-1">
          {[
            { label: "Days Above Gate", value: `${daysAboveGate}/90` },
            {
              label: "Current Streak",
              value: `${currentStreak > 0 ? "+" : ""}${currentStreak}d`,
            },
            { label: "Best Window", value: `${bestPct.toFixed(1)}%` },
            { label: "Gap to Gate", value: `${(55 - pct).toFixed(1)}pp` },
          ].map((s) => (
            <div key={s.label} className="bg-[var(--color-surface)] p-3">
              <span className="block font-mono text-[8px] tracking-wider text-[var(--color-text-muted)] uppercase">
                {s.label}
              </span>
              <span className="block font-mono text-[16px] font-medium text-[var(--color-text)] tabular-nums">
                {s.value}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
