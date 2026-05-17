"use client";

import { SampleSizeBadge } from "@/components/ui/sample-size-badge";
import { classifyRegime } from "@/lib/regime-classifier";
import { fmtPropCI, wilsonCI } from "@/lib/stats";
import type { RegimeBreakdownRow } from "@/lib/supabase/queries";

interface RegimeBreakdownProps {
  rows: RegimeBreakdownRow[];
  horizon: "t5" | "t20";
}

export function RegimeBreakdown({ rows, horizon }: RegimeBreakdownProps) {
  // Group by pair, then by regime type
  const byPair = new Map<
    string,
    Map<string, { correct: number; total: number }>
  >();

  for (const r of rows) {
    if (!byPair.has(r.pair)) byPair.set(r.pair, new Map());
    const pairMap = byPair.get(r.pair);
    if (!pairMap) continue;

    const type = classifyRegime(r.regime);
    const outcome = horizon === "t5" ? r.t5Outcome : r.t20Outcome;
    if (outcome === "—" || outcome === "NEUTRAL") continue;

    const curr = pairMap.get(type) ?? { correct: 0, total: 0 };
    curr.total += 1;
    if (outcome === "CORRECT") curr.correct += 1;
    pairMap.set(type, curr);
  }

  const PAIRS_ORDER = ["EUR/USD", "USD/JPY", "USD/INR", "ALL"];

  // ALL aggregate
  const allMap = new Map<string, { correct: number; total: number }>();
  for (const [, pairMap] of byPair) {
    for (const [type, stats] of pairMap) {
      const curr = allMap.get(type) ?? { correct: 0, total: 0 };
      curr.correct += stats.correct;
      curr.total += stats.total;
      allMap.set(type, curr);
    }
  }
  byPair.set("ALL", allMap);

  const regimeOrder: string[] = ["Risk-On", "Risk-Off", "Transitional"];

  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden mb-10">
      <div className="px-5 py-3 border-b border-[var(--color-border)]">
        <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
          Accuracy by Regime Type · {horizon.toUpperCase()}
        </p>
      </div>
      <div className="overflow-x-auto">
        <table
          className="w-full border-collapse font-mono text-[11px]"
          aria-label={`Regime breakdown ${horizon}`}
        >
          <thead>
            <tr className="border-b border-[var(--color-border)] bg-[var(--color-elevated)]">
              <th
                scope="col"
                className="px-4 py-2.5 text-left text-[9px] text-[var(--color-text-muted)] tracking-[0.15em] font-semibold uppercase whitespace-nowrap"
              >
                PAIR
              </th>
              {regimeOrder.map((rt) => (
                <th
                  key={rt}
                  scope="col"
                  className="px-4 py-2.5 text-left text-[9px] text-[var(--color-text-muted)] tracking-[0.15em] font-semibold uppercase whitespace-nowrap"
                >
                  {rt}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {PAIRS_ORDER.map((pairLabel, pi) => {
              const pairMap = byPair.get(pairLabel);
              if (!pairMap) return null;

              return (
                <tr
                  key={pairLabel}
                  className={`border-b border-[var(--color-border-subtle)] last:border-b-0 ${pi % 2 === 1 ? "bg-[var(--color-elevated)]" : "bg-[var(--color-surface)]"}`}
                >
                  <th
                    scope="row"
                    className="px-4 py-2.5 text-[var(--color-text-secondary)] whitespace-nowrap font-medium text-left"
                  >
                    {pairLabel}
                  </th>
                  {regimeOrder.map((rt) => {
                    const stats = pairMap.get(rt);
                    if (!stats || stats.total === 0) {
                      return (
                        <td
                          key={rt}
                          className="px-4 py-2.5 text-[var(--color-text-muted)]"
                        >
                          —
                        </td>
                      );
                    }
                    const rate = stats.correct / stats.total;
                    const ci = wilsonCI(stats.correct, stats.total);
                    const isSmall = stats.total < 30;

                    return (
                      <td key={rt} className="px-4 py-2.5">
                        <div className="flex flex-col gap-0.5">
                          <span
                            className={`tabular-nums ${isSmall ? "text-[var(--color-text-muted)]" : "text-[var(--color-text)]"}`}
                          >
                            {fmtPropCI(rate, ci)}
                          </span>
                          <SampleSizeBadge n={stats.total} />
                        </div>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
