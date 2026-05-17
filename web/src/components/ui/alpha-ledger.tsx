"use client";

import type { StrategyLedgerRow } from "@/lib/queries";
import { useMemo } from "react";

/** Rows from useStrategyLedger (non-neutral directional ledger). */
export type AlphaLedgerRow = Pick<
  StrategyLedgerRow,
  | "id"
  | "regime"
  | "date"
  | "direction"
  | "t1_hit"
  | "t3_hit"
  | "t5_hit"
  | "brier_score_t5"
  | "max_pain_bps"
>;

/** Swiss audit: hit / miss / neutral as luminance + weight only. */
export function hitAuditMark(v: number | null | undefined): string {
  if (v === 1) return "[ ✓ ]";
  if (v === 0) return "[ ✕ ]";
  return "[ = ]";
}

function hitAuditClass(v: number | null | undefined): string {
  if (v === 1) return "text-white font-bold";
  if (v === 0) return "text-[#555] font-light";
  return "text-[#888] font-normal";
}

function regimeCycleTitle(regime: string): string {
  const t = regime.trim().replace(/_/g, " ");
  if (!t) return "UNKNOWN CYCLE";
  return `${t.toUpperCase()} CYCLE`;
}

type RegimeGroup = { regime: string; items: AlphaLedgerRow[] };

function groupByRegime(rows: AlphaLedgerRow[]): RegimeGroup[] {
  const m = new Map<string, AlphaLedgerRow[]>();
  for (const r of rows) {
    const key = r.regime || "UNKNOWN";
    const list = m.get(key) ?? [];
    list.push(r);
    m.set(key, list);
  }
  const out: RegimeGroup[] = [];
  for (const [regime, items] of m) {
    items.sort((a, b) => b.date.localeCompare(a.date));
    out.push({ regime, items });
  }
  out.sort((a, b) => {
    const da = a.items[0]?.date ?? "";
    const db = b.items[0]?.date ?? "";
    return db.localeCompare(da);
  });
  return out;
}

type AlphaLedgerProps = {
  rows: AlphaLedgerRow[];
};

/** Fixed audit columns: date / regime / direction / T+1 / T+3 / T+5 / Brier (90d). */
const LEDGER_GRID =
  "minmax(5.5rem,1fr) minmax(7rem,1.15fr) minmax(4.25rem,0.85fr) 4.25rem 4.25rem 4.25rem 100px" as const;

function BrierSparkline({ dataPoints }: { dataPoints: number[] }) {
  if (!dataPoints || dataPoints.length === 0)
    return <div className="h-[30px] w-[100px] bg-[#111] opacity-20" />;

  const w = 100;
  const h = 30;

  // Brier score is 0..1 (0 is best, 1 is worst)
  const minVal = 0;
  const maxVal = 1;

  const pts = dataPoints.map((val, i) => {
    const x = dataPoints.length > 1 ? (i / (dataPoints.length - 1)) * w : w;
    // Lower Brier is better. Brier 0 at bottom (y=h), Brier 1 at top (y=0)
    const y = h - ((val - minVal) / (maxVal - minVal)) * h;
    return `${x},${y}`;
  });

  const latestBrier = dataPoints[dataPoints.length - 1];
  const color =
    latestBrier < 0.25 ? "#10b981" : latestBrier > 0.5 ? "#ef4444" : "#666666";

  return (
    <div className="flex flex-col items-center">
      <svg
        width={w}
        height={h}
        viewBox={`0 0 ${w} ${h}`}
        className="overflow-visible"
      >
        <title>Alpha Ledger Chart</title>
        {/* Baseline (Brier = 0.25, arbitrary "good" threshold) */}
        <line
          x1={0}
          y1={h * 0.75}
          x2={w}
          y2={h * 0.75}
          stroke="#333"
          strokeWidth={1}
          strokeDasharray="2 2"
          strokeOpacity={0.5}
        />
        {dataPoints.length === 1 ? (
          <circle
            cx={w}
            cy={h - ((latestBrier - minVal) / (maxVal - minVal)) * h}
            r={1.5}
            fill={color}
          />
        ) : (
          <polyline
            fill="none"
            stroke={color}
            strokeWidth={1.5}
            points={pts.join(" ")}
          />
        )}
      </svg>
    </div>
  );
}

export function AlphaLedger({ rows }: AlphaLedgerProps) {
  const groups = useMemo(() => groupByRegime(rows), [rows]);

  // Pre-calculate 90-day Brier sliding window for all rows in O(N log N)
  const brierMap = useMemo(() => {
    const map = new Map<string, number[]>();
    const parsed = rows
      .map((r) => ({
        id: r.id,
        time: new Date(r.date).getTime(),
        brier: r.brier_score_t5,
      }))
      .sort((a, b) => a.time - b.time);

    const msIn90Days = 90 * 24 * 60 * 60 * 1000;

    let left = 0;
    for (let right = 0; right < parsed.length; right++) {
      while (parsed[right].time - parsed[left].time > msIn90Days) {
        left++;
      }
      const window: number[] = [];
      for (let i = left; i <= right; i++) {
        const val = parsed[i].brier;
        if (val !== null && val !== undefined) {
          window.push(val);
        }
      }
      map.set(parsed[right].id, window);
    }
    return map;
  }, [rows]);

  if (groups.length === 0) {
    return (
      <div className="border border-solid border-[#111] bg-[#000000] px-4 py-8 text-center font-mono text-[11px] tabular-nums text-[var(--text-muted)] shadow-none">
        No ledger rows for this pair.
      </div>
    );
  }

  return (
    <div className="space-y-12 shadow-none">
      {groups.map((g, gi) => (
        <section key={g.regime} className="w-full shadow-none">
          <h2
            className={`mb-4 border-0 font-serif text-2xl font-light tracking-tight text-[#d4d4d4] shadow-none md:text-3xl ${gi === 0 ? "mt-0" : ""}`}
          >
            {regimeCycleTitle(g.regime)}
          </h2>
          <div className="w-full overflow-x-auto border border-solid border-[#111] bg-[#000000] shadow-none">
            <div
              className="grid w-full min-w-[700px]"
              style={{
                gridTemplateColumns: LEDGER_GRID,
              }}
            >
              {(
                [
                  "Date",
                  "Regime",
                  "Direction",
                  "T+1",
                  "T+3",
                  "T+5",
                  "Brier (90d)",
                ] as const
              ).map((h) => (
                <div
                  key={h}
                  className="border-b border-r border-solid border-[#222] px-2 py-2 font-mono text-[9px] tracking-widest text-[var(--text-muted)] shadow-none last:border-r-0"
                >
                  {h}
                </div>
              ))}
              {g.items.flatMap((r) => {
                const baseCell =
                  "border-b border-r border-solid border-[#111] px-2 py-2 flex items-center font-mono text-[11px] tabular-nums text-[#e8e8e8] shadow-none";
                return [
                  <div key={`${r.id}-d`} className={baseCell}>
                    {r.date}
                  </div>,
                  <div key={`${r.id}-reg`} className={baseCell}>
                    {r.regime.replace(/_/g, " ")}
                  </div>,
                  <div key={`${r.id}-dir`} className={baseCell}>
                    {r.direction}
                  </div>,
                  <div
                    key={`${r.id}-t1`}
                    className={`${baseCell} justify-center font-mono tabular-nums ${hitAuditClass(r.t1_hit)}`}
                  >
                    {hitAuditMark(r.t1_hit)}
                  </div>,
                  <div
                    key={`${r.id}-t3`}
                    className={`${baseCell} justify-center font-mono tabular-nums ${hitAuditClass(r.t3_hit)}`}
                  >
                    {hitAuditMark(r.t3_hit)}
                  </div>,
                  <div
                    key={`${r.id}-t5`}
                    className={`${baseCell} justify-center font-mono tabular-nums ${hitAuditClass(r.t5_hit)}`}
                  >
                    {hitAuditMark(r.t5_hit)}
                  </div>,
                  <div
                    key={`${r.id}-brier`}
                    className={`${baseCell} justify-center border-r-0 p-0`}
                  >
                    <BrierSparkline dataPoints={brierMap.get(r.id) ?? []} />
                  </div>,
                ];
              })}
            </div>
          </div>
        </section>
      ))}
    </div>
  );
}
