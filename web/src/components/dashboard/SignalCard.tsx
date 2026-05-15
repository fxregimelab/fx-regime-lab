import { ConfidenceBar } from "@/components/ui/confidence-bar";
import { Sparkline } from "@/components/ui/sparkline";
import { fmt2, fmtInt, fmtPct } from "@/components/ui/utils";
import { PAIRS } from "@/lib/constants";
import type { LatestRegimeCall, LatestSignal } from "@/lib/supabase/queries";
import Link from "next/link";

interface SignalCardProps {
  pairLabel: string;
  call?: LatestRegimeCall | null;
  signal?: LatestSignal | null;
  signalHistory?: number[];
  regimeHistory?: Array<{ date: string; regime: string }>;
  rolling90dAccuracyT5?: number | null;
  rolling90dAccuracyT20?: number | null;
}

export function SignalCard({
  pairLabel,
  call,
  signal,
  signalHistory,
  regimeHistory,
  rolling90dAccuracyT5,
  rolling90dAccuracyT20,
}: SignalCardProps) {
  const pairMeta = PAIRS.find((p) => p.label === pairLabel);
  const chg = signal?.day_change_pct;

  // Regime age: days since last regime change
  // regimeHistory is descending (latest first)
  let regimeAge: number | null = null;
  if (regimeHistory && regimeHistory.length >= 2) {
    const currentRegime = regimeHistory[0].regime;
    let daysSinceChange = 0;
    for (let i = 1; i < regimeHistory.length; i++) {
      if (regimeHistory[i].regime !== currentRegime) {
        break;
      }
      daysSinceChange++;
    }
    regimeAge = daysSinceChange;
  }

  return (
    <Link
      href={`/terminal/fx-regime/${pairMeta?.urlSlug ?? pairLabel.toLowerCase()}`}
      className="block bg-[var(--color-surface)] border border-[var(--color-border)] transition-colors hover:bg-[var(--color-elevated)]"
    >
      {/* Header */}
      <div className="px-5 py-4 border-b border-[var(--color-border)]">
        <div className="flex justify-between items-center mb-3">
          <span
            className="font-mono text-[11px] font-bold tracking-wider"
            style={{ color: pairMeta?.pairColor ?? "#ccc" }}
          >
            {pairMeta?.display ?? pairLabel}
          </span>
          <div className="flex items-center gap-3">
            {rolling90dAccuracyT5 != null && (
              <span className="font-mono text-[9px] text-[var(--color-text-muted)] tabular-nums">
                90D:{(rolling90dAccuracyT5 * 100).toFixed(1)}%
              </span>
            )}
            {chg != null && (
              <span
                className={`font-mono text-[10px] font-medium ${
                  chg >= 0
                    ? "text-[var(--color-up)]"
                    : "text-[var(--color-down)]"
                }`}
              >
                {chg >= 0 ? "+" : ""}
                {chg.toFixed(2)}%
              </span>
            )}
          </div>
        </div>
        <div className="flex items-baseline gap-3">
          <p className="font-mono text-[28px] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">
            {signal?.spot?.toFixed(pairLabel === "USDJPY" ? 2 : 4) ?? "—"}
          </p>
          <p className="font-mono text-[10px] text-[var(--color-text-secondary)] font-medium tracking-wider">
            {call?.regime ?? "—"}
          </p>
        </div>
      </div>

      {/* Sparkline */}
      {signalHistory && signalHistory.length >= 2 && (
        <div className="px-5 py-3 border-b border-[var(--color-border)]">
          <Sparkline
            data={signalHistory}
            width={240}
            height={40}
            color={pairMeta?.pairColor}
          />
        </div>
      )}

      {/* Layer 1 — Regime Gate */}
      <div className="px-5 py-3 border-b border-[var(--color-border-subtle)]">
        <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-2">
          Layer 1 — Regime Gate
        </p>
        <div className="flex justify-between items-center">
          <span className="font-mono text-[11px] text-[var(--color-text-secondary)]">
            {call?.regime ?? "—"}
          </span>
          {regimeAge != null && (
            <span className="font-mono text-[9px] text-[var(--color-text-muted)] tabular-nums">
              {regimeAge}D
            </span>
          )}
        </div>
      </div>

      {/* Layer 2 — Directional */}
      <div className="px-5 py-3 border-b border-[var(--color-border-subtle)]">
        <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-2">
          Layer 2 — Directional
        </p>
        <div className="grid grid-cols-2 gap-2">
          <div className="flex justify-between">
            <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
              RATE
            </span>
            <span className="font-mono text-[10px] text-[var(--color-text)] font-medium">
              {call?.rate_signal ?? "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
              COT
            </span>
            <span className="font-mono text-[10px] text-[var(--color-text)] font-medium tabular-nums">
              {pairLabel === "USDINR" ? "N/A" : fmtInt(signal?.cot_percentile)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
              COMP
            </span>
            <span className="font-mono text-[10px] text-[var(--color-text)] font-medium tabular-nums">
              {fmt2(call?.signal_composite)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
              RVOL
            </span>
            <span className="font-mono text-[10px] text-[var(--color-text)] font-medium tabular-nums">
              {fmt2(signal?.realized_vol_20d)}
            </span>
          </div>
        </div>
      </div>

      {/* Layer 3 — Execution */}
      <div className="px-5 py-3 border-b border-[var(--color-border-subtle)]">
        <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-2">
          Layer 3 — Execution
        </p>
        <div className="grid grid-cols-2 gap-2">
          <div className="flex justify-between">
            <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
              ENTRY
            </span>
            <span className="font-mono text-[10px] text-[var(--color-text)] font-medium">
              {call?.entry_timing ?? "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
              SIZE
            </span>
            <span className="font-mono text-[10px] text-[var(--color-text)] font-medium">
              {call?.position_size ?? "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
              STOP
            </span>
            <span className="font-mono text-[10px] text-[var(--color-text)] font-medium tabular-nums">
              {call?.stop_level != null
                ? call.stop_level.toFixed(pairLabel === "USDJPY" ? 2 : 4)
                : "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
              RVOL RANK
            </span>
            <span className="font-mono text-[10px] text-[var(--color-text)] font-medium tabular-nums">
              {fmtInt(signal?.realized_vol_rank)}
            </span>
          </div>
        </div>
      </div>

      {/* Confidence */}
      <div className="px-5 py-3">
        <div className="flex justify-between items-center mb-1.5">
          <span className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-[0.1em]">
            CONF
          </span>
          <span className="font-mono text-[10px] text-[var(--color-text)] font-bold">
            {fmtPct(call?.confidence)}
          </span>
        </div>
        <ConfidenceBar
          value={call?.confidence}
          tone="dark"
          color={pairMeta?.pairColor}
        />
        {call?.primary_driver && (
          <p className="font-mono text-[9px] text-[var(--color-text-muted)] mt-2 truncate">
            {call.primary_driver}
          </p>
        )}
      </div>
    </Link>
  );
}
