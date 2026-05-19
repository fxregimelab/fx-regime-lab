"use client";

import { ConfidenceBar } from "@/components/ui/confidence-bar";
import { DataLineage, LINEAGE } from "@/components/ui/data-lineage";
import {
  FreshnessIndicator,
  freshnessHaloClass,
  useFreshness,
} from "@/components/ui/freshness-indicator";
import { ReproducibilityExport } from "@/components/ui/reproducibility-export";
import { Sparkline } from "@/components/ui/sparkline";
import {
  fmt2,
  fmtConfidence,
  fmtInt,
  normalizeProp,
  timeAgo,
} from "@/components/ui/utils";
import { spotDecimals } from "@/lib/config";
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
  const { level: freshnessLevel } = useFreshness(
    signal?.created_at ?? call?.created_at,
  );

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
      className={`block bg-[var(--color-surface)] border border-[var(--color-border)] transition-colors hover:bg-[var(--color-elevated)] ${freshnessHaloClass(freshnessLevel)}`}
    >
      {/* Header */}
      <div className="px-5 py-4 border-b border-[var(--color-border)]">
        <div className="flex justify-between items-center mb-3">
          <span
            className="font-mono text-[11px] font-bold tracking-wider"
            style={{
              color: pairMeta?.pairColor ?? "var(--color-text-secondary)",
            }}
          >
            {pairMeta?.display ?? pairLabel}
          </span>
          <div className="flex items-center gap-3">
            <ReproducibilityExport
              payload={{
                query: "getLatestRegimeCalls + getLatestSignals",
                parameters: {
                  pair: pairLabel,
                  date:
                    call?.date ??
                    signal?.date ??
                    new Date().toISOString().slice(0, 10),
                },
                timestamp: new Date().toISOString(),
                dataVersion: call?.model_version ?? "v3",
                sourceTable: "regime_calls, signals",
              }}
              variant="icon"
            />
            <FreshnessIndicator
              lastUpdatedAt={signal?.created_at ?? call?.created_at}
              dot
            />
            <span
              className={`font-mono text-[9px] tabular-nums ${freshnessLevel === "aging" || freshnessLevel === "stale" ? "text-[var(--color-warn)]" : "text-[var(--color-text-muted)]"}`}
            >
              {timeAgo(signal?.created_at ?? call?.created_at ?? undefined)}
            </span>
            {rolling90dAccuracyT5 != null && (
              <span className="font-mono text-[9px] text-[var(--color-text-muted)] tabular-nums">
                ACC:
                {((normalizeProp(rolling90dAccuracyT5) ?? 0) * 100).toFixed(1)}%
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
          <DataLineage lineage={LINEAGE.spot(signal)}>
            <p className="font-mono text-[28px] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">
              {signal?.spot?.toFixed(spotDecimals(pairLabel)) ?? "—"}
            </p>
          </DataLineage>
          <DataLineage lineage={LINEAGE.regime(call)}>
            <p className="font-mono text-[10px] text-[var(--color-text-secondary)] font-medium tracking-wider">
              {(call?.regime ?? "—").replace(/_/g, " ")}
            </p>
          </DataLineage>
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
          <DataLineage lineage={LINEAGE.regime(call)}>
            <span className="font-mono text-[11px] text-[var(--color-text-secondary)]">
              {(call?.regime ?? "—").replace(/_/g, " ")}
            </span>
          </DataLineage>
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
            <DataLineage lineage={LINEAGE.rateSignal(call)}>
              <span className="font-mono text-[10px] text-[var(--color-text)] font-medium">
                {call?.rate_signal ?? "—"}
              </span>
            </DataLineage>
          </div>
          <div className="flex justify-between">
            <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
              COT
            </span>
            <DataLineage lineage={LINEAGE.cotPercentile(signal)}>
              <span className="font-mono text-[10px] text-[var(--color-text)] font-medium tabular-nums">
                {pairLabel === "USDINR"
                  ? "N/A"
                  : fmtInt(signal?.cot_percentile)}
              </span>
            </DataLineage>
          </div>
          <div className="flex justify-between">
            <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
              COMP
            </span>
            <DataLineage lineage={LINEAGE.composite(call)}>
              <span className="font-mono text-[10px] text-[var(--color-text)] font-medium tabular-nums">
                {fmt2(call?.signal_composite)}
              </span>
            </DataLineage>
          </div>
          <div className="flex justify-between">
            <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
              RVOL
            </span>
            <DataLineage lineage={LINEAGE.rvol(signal)}>
              <span className="font-mono text-[10px] text-[var(--color-text)] font-medium tabular-nums">
                {fmt2(signal?.realized_vol_20d)}
              </span>
            </DataLineage>
          </div>
          <div className="flex justify-between">
            <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
              RR 25D
            </span>
            <DataLineage lineage={LINEAGE.riskReversal(signal)}>
              <span
                className={`font-mono text-[10px] font-medium tabular-nums ${signal?.risk_reversal_25d == null ? "text-[var(--color-text-muted)]" : "text-[var(--color-text)]"}`}
              >
                {signal?.risk_reversal_25d != null
                  ? signal.risk_reversal_25d.toFixed(2)
                  : "—"}
              </span>
            </DataLineage>
          </div>
          <div className="flex justify-between">
            <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
              SKEW
            </span>
            <DataLineage lineage={LINEAGE.skew(signal)}>
              <span
                className={`font-mono text-[10px] font-medium tabular-nums ${signal?.skew_alignment == null ? "text-[var(--color-text-muted)]" : "text-[var(--color-text)]"}`}
              >
                {signal?.skew_alignment != null
                  ? signal.skew_alignment.toFixed(0)
                  : "—"}
              </span>
            </DataLineage>
          </div>
          {pairLabel === "USDINR" && (
            <div className="flex justify-between">
              <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
                FPI (Cr)
              </span>
              <DataLineage lineage={LINEAGE.fpi(signal)}>
                <span
                  className={`font-mono text-[10px] font-medium tabular-nums ${signal?.fpi_flow == null ? "text-[var(--color-text-muted)]" : "text-[var(--color-text)]"}`}
                >
                  {signal?.fpi_flow != null ? signal.fpi_flow.toFixed(0) : "—"}
                </span>
              </DataLineage>
            </div>
          )}
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
            <DataLineage lineage={LINEAGE.entryTiming(call)}>
              <span className="font-mono text-[10px] text-[var(--color-text)] font-medium">
                {call?.entry_timing ?? "—"}
              </span>
            </DataLineage>
          </div>

          <div className="flex justify-between">
            <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
              RVOL RANK
            </span>
            <DataLineage lineage={LINEAGE.rvolRank(signal)}>
              <span className="font-mono text-[10px] text-[var(--color-text)] font-medium tabular-nums">
                {fmtInt(signal?.realized_vol_rank)}
              </span>
            </DataLineage>
          </div>
        </div>
      </div>

      {/* Confidence */}
      <div className="px-5 py-3">
        <div className="flex justify-between items-center mb-1.5">
          <span className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-[0.1em]">
            CONF
          </span>
          <DataLineage lineage={LINEAGE.confidence(call)}>
            <span className="font-mono text-[10px] text-[var(--color-text)] font-bold">
              {fmtConfidence(call?.confidence)}
            </span>
          </DataLineage>
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
