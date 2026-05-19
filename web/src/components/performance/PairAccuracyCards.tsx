import { SampleSizeBadge } from "@/components/ui/sample-size-badge";
import { normalizeProp } from "@/components/ui/utils";
import { PAIRS } from "@/lib/constants";
import type { ValidationStats } from "@/lib/supabase/queries";

interface PairAccuracyCardsProps {
  statsT5: ValidationStats[];
  statsT20: ValidationStats[];
}

function fmtPct(n: number | null | undefined) {
  if (n == null) return "—";
  const prop = normalizeProp(n) ?? 0;
  const sign = prop >= 0 ? "+" : "";
  return `${sign}${(prop * 100).toFixed(1)}%`;
}

function fmtBrier(n: number | null | undefined) {
  if (n == null) return "—";
  return n.toFixed(3);
}

function TrendArrow({
  current,
  prior,
}: {
  current: number | null | undefined;
  prior: number | null | undefined;
}) {
  if (current == null || prior == null) return null;
  const diff = current - prior;
  if (Math.abs(diff) < 0.001) return null;
  const color = diff > 0 ? "var(--color-up)" : "var(--color-down)";
  return (
    <span
      className="font-mono text-[10px] tabular-nums ml-1.5"
      style={{ color }}
      title={`Δ ${diff > 0 ? "+" : ""}${(diff * 100).toFixed(1)}pp vs 90d`}
    >
      {diff > 0 ? "↑" : "↓"}
    </span>
  );
}

export function PairAccuracyCards({
  statsT5,
  statsT20,
}: PairAccuracyCardsProps) {
  const t5Map = new Map(statsT5.map((s) => [s.pair, s]));
  const t20Map = new Map(statsT20.map((s) => [s.pair, s]));

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-[var(--color-border)] border border-[var(--color-border)] mb-10">
      {PAIRS.map((p) => {
        const t5 = t5Map.get(p.display);
        const t20 = t20Map.get(p.display);

        const winRateColor = (v: number | null | undefined) => {
          if (v == null) return "var(--color-text-muted)";
          const prop = normalizeProp(v) ?? 0;
          if (prop >= 0.6) return "var(--color-up)";
          if (prop >= 0.5) return "var(--color-warn)";
          return "var(--color-down)";
        };

        return (
          <div
            key={p.label}
            className="bg-[var(--color-surface)] p-5 md:p-6 relative"
          >
            {/* Pair-colored top accent */}
            <div
              className="absolute top-0 left-0 right-0 h-[2px]"
              style={{ backgroundColor: p.pairColor }}
            />

            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span
                  className="inline-block w-2 h-2"
                  style={{ backgroundColor: p.pairColor }}
                />
                <p
                  className="font-mono text-[10px] tracking-[0.15em] uppercase font-bold"
                  style={{ color: p.pairColor }}
                >
                  {p.display}
                </p>
              </div>
              <SampleSizeBadge n={t5?.sampleSize ?? null} />
            </div>

            {/* T+5 Win Rate */}
            <div className="mb-3">
              <div className="flex items-baseline gap-2">
                <span
                  className="font-mono text-[clamp(22px,3vw,28px)] font-medium tracking-tight leading-none tabular-nums"
                  style={{ color: winRateColor(t5?.winRate) }}
                >
                  {fmtPct(t5?.winRate)}
                </span>
                <TrendArrow
                  current={t5?.winRate}
                  prior={t5?.rolling90dAccuracy}
                />
              </div>
              <p className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-wider mt-1">
                T+5 WIN RATE · {t5?.sampleSize ?? "—"} CALLS
              </p>
            </div>

            {/* Divider */}
            <div className="h-px bg-[var(--color-border-subtle)] my-3" />

            {/* T+20 Win Rate */}
            <div className="mb-3">
              <div className="flex items-baseline gap-2">
                <span
                  className="font-mono text-[clamp(18px,2.5vw,22px)] font-medium tracking-tight leading-none tabular-nums"
                  style={{ color: winRateColor(t20?.winRate) }}
                >
                  {fmtPct(t20?.winRate)}
                </span>
                <TrendArrow
                  current={t20?.winRate}
                  prior={t20?.rolling90dAccuracy}
                />
              </div>
              <p className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-wider mt-1">
                T+20 WIN RATE · {t20?.sampleSize ?? "—"} CALLS
              </p>
            </div>

            {/* Divider */}
            <div className="h-px bg-[var(--color-border-subtle)] my-3" />

            {/* Bottom row: Brier + 90d */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-wider mb-0.5">
                  T+5 BRIER
                </p>
                <p className="font-mono text-[13px] tabular-nums text-[var(--color-text)]">
                  {fmtBrier(t5?.brierScore)}
                </p>
              </div>
              <div>
                <p className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-wider mb-0.5">
                  90D ROLLING
                </p>
                <p
                  className="font-mono text-[13px] tabular-nums"
                  style={{ color: winRateColor(t5?.rolling90dAccuracy) }}
                >
                  {fmtPct(t5?.rolling90dAccuracy)}
                </p>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
