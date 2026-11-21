import { normalizeProp } from "@/components/ui/utils";
import { PAIRS } from "@/lib/constants";
import type { ValidationStats } from "@/lib/supabase/queries";

interface PairAccuracyCardsProps {
  statsT5: ValidationStats[];
  statsT20: ValidationStats[];
}

function fmtPct(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) return "—";
  const prop = normalizeProp(value) ?? 0;
  return `${(prop * 100).toFixed(1)}%`;
}

export function PairAccuracyCards({
  statsT5,
  statsT20,
}: PairAccuracyCardsProps) {
  const t5Map = new Map(statsT5.map((stats) => [stats.pair, stats]));
  const t20Map = new Map(statsT20.map((stats) => [stats.pair, stats]));

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-[var(--color-border)] border border-[var(--color-border)] mb-10">
      {PAIRS.map((pair) => {
        const t5 = t5Map.get(pair.display);
        const t20 = t20Map.get(pair.display);
        return (
          <div
            key={pair.label}
            className="bg-[var(--color-surface)] p-5 md:p-6 relative"
          >
            <div
              className="absolute top-0 left-0 right-0 h-[2px]"
              style={{ backgroundColor: pair.pairColor }}
            />
            <p
              className="font-mono text-[10px] tracking-[0.15em] uppercase font-bold mb-4"
              style={{ color: pair.pairColor }}
            >
              {pair.display}
            </p>
            <div className="grid grid-cols-2 gap-5">
              {(
                [
                  ["T+5", t5],
                  ["T+20", t20],
                ] as const
              ).map(([label, stats]) => (
                <div key={label}>
                  <p className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-wider mb-1">
                    {label} ACCURACY
                  </p>
                  <p className="font-mono text-[22px] text-[var(--color-text)] tabular-nums">
                    {fmtPct(stats?.winRate)}
                  </p>
                  <p className="font-mono text-[9px] text-[var(--color-text-muted)] mt-1">
                    {stats?.directionalCalls ?? 0} SCORED /{" "}
                    {stats?.totalCalls ?? 0} PUBLISHED CALLS
                  </p>
                  <p className="font-mono text-[9px] text-[var(--color-text-muted)] mt-1">
                    SCORED SHARE {fmtPct(stats?.coverage)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
