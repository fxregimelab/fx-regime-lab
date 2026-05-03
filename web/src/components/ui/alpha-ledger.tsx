'use client';

import { useMemo } from 'react';
import type { StrategyLedgerRow } from '@/lib/queries';

/** Rows from useStrategyLedger (non-neutral directional ledger). */
export type AlphaLedgerRow = Pick<
  StrategyLedgerRow,
  'regime' | 'date' | 't1_hit' | 't3_hit' | 't5_hit' | 'brier_score_t5' | 'max_pain_bps'
>;

/** Brier at p=0.5 forecast is 0.25; scores above this imply worse-than-chance calibration. */
const BRIER_COIN_FLIP = 0.25;
const SPARK_W = 88;
const SPARK_H = 22;

function isHitScored(v: number | null | undefined): v is number {
  return v != null && v !== -1;
}

function hitWinRatePct(rows: AlphaLedgerRow[], key: 't1_hit' | 't3_hit' | 't5_hit'): number | null {
  const scored = rows.filter((r) => isHitScored(r[key]));
  if (scored.length === 0) return null;
  const wins = scored.filter((r) => r[key] === 1).length;
  return (wins / scored.length) * 100;
}

function avgBrier(rows: AlphaLedgerRow[]): number | null {
  const vals = rows
    .map((r) => r.brier_score_t5)
    .filter((x): x is number => typeof x === 'number' && !Number.isNaN(x));
  if (vals.length === 0) return null;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

function avgMaxPainBps(rows: AlphaLedgerRow[]): number | null {
  const vals = rows
    .map((r) => r.max_pain_bps)
    .filter((x): x is number => typeof x === 'number' && !Number.isNaN(x));
  if (vals.length === 0) return null;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

function rollingMean(vals: number[], window: number): number[] {
  if (vals.length === 0) return [];
  const w = Math.max(1, window);
  const out: number[] = [];
  for (let i = 0; i < vals.length; i++) {
    const start = Math.max(0, i - w + 1);
    const slice = vals.slice(start, i + 1);
    out.push(slice.reduce((a, b) => a + b, 0) / slice.length);
  }
  return out;
}

function brierSeriesForRegime(rows: AlphaLedgerRow[], regime: string): number[] {
  const subset = rows
    .filter((r) => r.regime === regime)
    .filter((r) => typeof r.brier_score_t5 === 'number' && !Number.isNaN(r.brier_score_t5))
    .sort((a, b) => a.date.localeCompare(b.date));
  return subset.map((r) => r.brier_score_t5 as number);
}

function sparkPathYs(series: number[], width: number, height: number): string {
  if (series.length === 0) return '';
  const n = series.length;
  const pts: string[] = [];
  for (let i = 0; i < n; i++) {
    const x = n === 1 ? width / 2 : (i / (n - 1)) * width;
    const v = Math.min(1, Math.max(0, series[i]!));
    const y = height - v * height;
    pts.push(`${x.toFixed(2)},${y.toFixed(2)}`);
  }
  return `M ${pts.join(' L ')}`;
}

function DualBrierSparkline({ s90, s5 }: { s90: number[]; s5: number[] }) {
  if (s90.length === 0 && s5.length === 0) {
    return (
      <span className="text-[9px] text-[#555] tabular-nums" aria-hidden>
        —
      </span>
    );
  }
  const p90 = sparkPathYs(s90, SPARK_W, SPARK_H);
  const p5 = sparkPathYs(s5, SPARK_W, SPARK_H);
  return (
    <svg
      width={SPARK_W}
      height={SPARK_H}
      viewBox={`0 0 ${SPARK_W} ${SPARK_H}`}
      className="tabular-nums"
      aria-label="Rolling Brier: white 90-observation, amber 5-observation"
    >
      {p90 ? (
        <path d={p90} fill="none" stroke="#f5f5f5" strokeWidth={1.1} vectorEffect="non-scaling-stroke" />
      ) : null}
      {p5 ? (
        <path d={p5} fill="none" stroke="#f59e0b" strokeWidth={1.1} vectorEffect="non-scaling-stroke" />
      ) : null}
    </svg>
  );
}

function edgeTone(pct: number | null): string {
  if (pct == null) return 'text-white';
  if (pct > 50) return 'text-[#22c55e]';
  if (pct < 50) return 'text-[#ef4444]';
  return 'text-white';
}

function formatEdge(pct: number | null): string {
  if (pct == null) return 'N/A';
  return `${pct.toFixed(1)}%`;
}

function formatBrier(v: number | null): string {
  if (v == null) return 'N/A';
  return v.toFixed(3);
}

function formatMaxPainBps(v: number | null): string {
  if (v == null) return 'N/A';
  return `${v.toFixed(1)}`;
}

function statusFor(
  t5Edge: number | null,
  n: number,
  degraded: boolean,
): { label: string; className: string } {
  if (degraded) return { label: '[ SIGNAL DEGRADED ]', className: 'text-[#f59e0b]' };
  if (n >= 5 && t5Edge != null) {
    if (t5Edge < 50) return { label: '[ DECAYED ]', className: 'text-[#ef4444]' };
    if (t5Edge >= 60) return { label: '[ HIGH CONVICTION ]', className: 'text-[#22c55e]' };
  }
  return { label: '[ ACTIVE ]', className: 'text-[#a3a3a3]' };
}

export type RegimeAgg = {
  regime: string;
  n: number;
  t1: number | null;
  t3: number | null;
  t5: number | null;
  brier: number | null;
  maxPainBps: number | null;
  spark90: number[];
  spark5: number[];
  degraded: boolean;
};

export function aggregateLedgerByRegime(rows: AlphaLedgerRow[]): RegimeAgg[] {
  const map = new Map<string, AlphaLedgerRow[]>();
  for (const r of rows) {
    const list = map.get(r.regime) ?? [];
    list.push(r);
    map.set(r.regime, list);
  }
  const out: RegimeAgg[] = [];
  for (const [regime, list] of map) {
    const series = brierSeriesForRegime(rows, regime);
    const spark90 = rollingMean(series, 90);
    const spark5 = rollingMean(series, 5);
    const lastAcute = spark5.length > 0 ? spark5[spark5.length - 1]! : null;
    const degraded = lastAcute != null && lastAcute > BRIER_COIN_FLIP;
    out.push({
      regime,
      n: list.length,
      t1: hitWinRatePct(list, 't1_hit'),
      t3: hitWinRatePct(list, 't3_hit'),
      t5: hitWinRatePct(list, 't5_hit'),
      brier: avgBrier(list),
      maxPainBps: avgMaxPainBps(list),
      spark90,
      spark5,
      degraded,
    });
  }
  out.sort((a, b) => b.n - a.n || a.regime.localeCompare(b.regime));
  return out;
}

type AlphaLedgerProps = {
  rows: AlphaLedgerRow[];
};

export function AlphaLedger({ rows }: AlphaLedgerProps) {
  const agg = useMemo(() => aggregateLedgerByRegime(rows), [rows]);

  return (
    <div
      className="grid w-full border border-solid border-[#111] bg-[#000000] text-white rounded-none"
      style={{
        gridTemplateColumns: '1.12fr 0.5fr 0.55fr 0.55fr 0.55fr 0.52fr 0.58fr 1.05fr 1fr',
      }}
    >
      {(
        [
          'Regime',
          'Sample (N)',
          'T+1 Edge',
          'T+3 Edge',
          'T+5 Edge',
          'Brier',
          'Max Pain (BPS)',
          'Fidelity',
          'Status',
        ] as const
      ).map((h) => (
        <div
          key={h}
          className="border-b border-r border-solid border-[#222] px-2 py-2 text-[9px] tracking-widest text-[#777] last:border-r-0"
        >
          {h}
        </div>
      ))}

      {agg.length === 0 ? (
        <div className="col-span-9 border-t border-solid border-[#111] px-2 py-6 text-center text-[11px] text-[#777] tabular-nums">
          No ledger rows for this pair.
        </div>
      ) : (
        agg.flatMap((row) => {
          const st = statusFor(row.t5, row.n, row.degraded);
          const rowDim = row.degraded ? 'opacity-40' : '';
          return [
            <div
              key={`${row.regime}-r`}
              className={`border-b border-r border-solid border-[#111] px-2 py-2 text-[11px] tabular-nums ${rowDim}`}
            >
              {row.regime}
            </div>,
            <div
              key={`${row.regime}-n`}
              className={`border-b border-r border-solid border-[#111] px-2 py-2 text-[11px] tabular-nums ${rowDim}`}
            >
              {row.n}
            </div>,
            <div
              key={`${row.regime}-t1`}
              className={`border-b border-r border-solid border-[#111] px-2 py-2 text-[11px] tabular-nums ${edgeTone(row.t1)} ${rowDim}`}
            >
              {formatEdge(row.t1)}
            </div>,
            <div
              key={`${row.regime}-t3`}
              className={`border-b border-r border-solid border-[#111] px-2 py-2 text-[11px] tabular-nums ${edgeTone(row.t3)} ${rowDim}`}
            >
              {formatEdge(row.t3)}
            </div>,
            <div
              key={`${row.regime}-t5`}
              className={`border-b border-r border-solid border-[#111] px-2 py-2 text-[11px] tabular-nums ${edgeTone(row.t5)} ${rowDim}`}
            >
              {formatEdge(row.t5)}
            </div>,
            <div
              key={`${row.regime}-b`}
              className={`border-b border-r border-solid border-[#111] px-2 py-2 text-[11px] tabular-nums text-white ${rowDim}`}
            >
              {formatBrier(row.brier)}
            </div>,
            <div
              key={`${row.regime}-mp`}
              className={`border-b border-r border-solid border-[#111] px-2 py-2 text-[11px] tabular-nums ${rowDim} ${
                row.maxPainBps != null && row.maxPainBps > 150 ? 'text-[#ef4444]' : 'text-white'
              }`}
            >
              {formatMaxPainBps(row.maxPainBps)}
            </div>,
            <div
              key={`${row.regime}-spark`}
              className={`border-b border-r border-solid border-[#111] px-1 py-1 flex items-center justify-center ${rowDim}`}
            >
              <DualBrierSparkline s90={row.spark90} s5={row.spark5} />
            </div>,
            <div
              key={`${row.regime}-s`}
              className={`border-b border-solid border-[#111] px-2 py-2 font-mono text-[10px] tracking-wide tabular-nums ${st.className} ${rowDim}`}
            >
              {st.label}
            </div>,
          ];
        })
      )}
    </div>
  );
}
