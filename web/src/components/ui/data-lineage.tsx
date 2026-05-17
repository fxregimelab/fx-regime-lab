"use client";

import type React from "react";

export interface LineageInfo {
  source: string;
  updatedAt?: string | null;
  transformation: string;
  rawValue?: string;
}

interface DataLineageProps {
  lineage: LineageInfo;
  children: React.ReactNode;
}

/** Terminal-styled tooltip showing data provenance.
 *  Triggered on hover (mouse) or focus (keyboard).
 */
export function DataLineage({ lineage, children }: DataLineageProps) {
  return (
    <div className="group relative inline-block cursor-help">
      {children}
      <div
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-[var(--z-tooltip)] mb-2 hidden w-[260px] -translate-x-1/2 border border-[var(--terminal-border-bright)] bg-[var(--terminal-bg-elevated)] p-3 shadow-lg group-hover:block group-focus:block"
        style={{ borderRadius: 2 }}
      >
        <span className="block font-mono text-[9px] tracking-widest text-[var(--terminal-warning)] uppercase mb-2">
          Data Lineage
        </span>

        <span className="block font-mono text-[9px] text-[var(--terminal-fg-dim)] uppercase tracking-wider mb-0.5">
          Source
        </span>
        <span className="block font-mono text-[10px] text-[var(--terminal-fg)] mb-2">
          {lineage.source}
        </span>

        {lineage.rawValue && (
          <>
            <span className="block font-mono text-[9px] text-[var(--terminal-fg-dim)] uppercase tracking-wider mb-0.5">
              Raw Value
            </span>
            <span className="block font-mono text-[10px] text-[var(--terminal-fg-muted)] mb-2">
              {lineage.rawValue}
            </span>
          </>
        )}

        <span className="block font-mono text-[9px] text-[var(--terminal-fg-dim)] uppercase tracking-wider mb-0.5">
          Transformation
        </span>
        <span className="block font-mono text-[10px] text-[var(--terminal-fg-muted)] mb-2">
          {lineage.transformation}
        </span>

        {lineage.updatedAt && (
          <>
            <span className="block font-mono text-[9px] text-[var(--terminal-fg-dim)] uppercase tracking-wider mb-0.5">
              Last Update
            </span>
            <span className="block font-mono text-[10px] text-[var(--terminal-fg-muted)]">
              {lineage.updatedAt}
            </span>
          </>
        )}

        {/* Arrow */}
        <span className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-[var(--terminal-border-bright)]" />
      </div>
    </div>
  );
}

/** Pre-configured lineage definitions for common signal fields. */
export const LINEAGE = {
  spot: (
    sig?: { spot: number | null; created_at?: string | null } | null,
  ): LineageInfo => ({
    source: "Market data (Bloomberg / Refinitiv)",
    updatedAt: sig?.created_at?.slice(0, 10) ?? null,
    transformation: "Spot mid-price, no smoothing",
    rawValue: sig?.spot != null ? sig.spot.toFixed(4) : undefined,
  }),
  regime: (
    call?: { regime: string | null; created_at?: string | null } | null,
  ): LineageInfo => ({
    source: "FX Regime Lab model v3",
    updatedAt: call?.created_at?.slice(0, 10) ?? null,
    transformation:
      "Weighted composite → regime classifier (RATE 40%, COT 30%, VOL 20%, OI 10%)",
    rawValue: call?.regime ?? undefined,
  }),
  rateSignal: (
    call?: { rate_signal: string | null; created_at?: string | null } | null,
  ): LineageInfo => ({
    source: "Central bank policy rates (2Y yield spread)",
    updatedAt: call?.created_at?.slice(0, 10) ?? null,
    transformation: "Rate diff → z-score → directional threshold",
    rawValue: call?.rate_signal ?? undefined,
  }),
  cotPercentile: (
    sig?: { cot_percentile: number | null; created_at?: string | null } | null,
  ): LineageInfo => ({
    source: "CFTC Commitment of Traders (COT)",
    updatedAt: sig?.created_at?.slice(0, 10) ?? null,
    transformation: "Net non-commercial position → 52-week percentile",
    rawValue:
      sig?.cot_percentile != null
        ? `${sig.cot_percentile.toFixed(1)}%`
        : undefined,
  }),
  composite: (
    call?: {
      signal_composite: number | null;
      created_at?: string | null;
    } | null,
  ): LineageInfo => ({
    source: "FX Regime Lab model v3",
    updatedAt: call?.created_at?.slice(0, 10) ?? null,
    transformation:
      "Weighted sum of normalized signals (RATE 40%, COT 30%, VOL 20%, OI 10%)",
    rawValue:
      call?.signal_composite != null
        ? call.signal_composite.toFixed(3)
        : undefined,
  }),
  rvol: (
    sig?: {
      realized_vol_20d: number | null;
      created_at?: string | null;
    } | null,
  ): LineageInfo => ({
    source: "Market realized volatility",
    updatedAt: sig?.created_at?.slice(0, 10) ?? null,
    transformation: "20-day annualized realized vol (%)",
    rawValue:
      sig?.realized_vol_20d != null
        ? `${sig.realized_vol_20d.toFixed(2)}%`
        : undefined,
  }),
  riskReversal: (
    sig?: {
      risk_reversal_25d: number | null;
      created_at?: string | null;
    } | null,
  ): LineageInfo => ({
    source: "FX options market (25-delta risk reversal)",
    updatedAt: sig?.created_at?.slice(0, 10) ?? null,
    transformation: "25D RR quote → skew sentiment indicator",
    rawValue:
      sig?.risk_reversal_25d != null
        ? sig.risk_reversal_25d.toFixed(2)
        : undefined,
  }),
  skew: (
    sig?: { skew_alignment: number | null; created_at?: string | null } | null,
  ): LineageInfo => ({
    source: "FX options market (skew term structure)",
    updatedAt: sig?.created_at?.slice(0, 10) ?? null,
    transformation: "Cross-tenor skew comparison → alignment score",
    rawValue:
      sig?.skew_alignment != null ? sig.skew_alignment.toFixed(0) : undefined,
  }),
  confidence: (
    call?: { confidence: number | null; created_at?: string | null } | null,
  ): LineageInfo => ({
    source: "FX Regime Lab model v3",
    updatedAt: call?.created_at?.slice(0, 10) ?? null,
    transformation: "Signal dispersion → confidence score (0–1)",
    rawValue:
      call?.confidence != null
        ? `${(call.confidence * 100).toFixed(1)}%`
        : undefined,
  }),
  fpi: (
    sig?: { fpi_flow: number | null; created_at?: string | null } | null,
  ): LineageInfo => ({
    source: "FPI flow data (India only)",
    updatedAt: sig?.created_at?.slice(0, 10) ?? null,
    transformation: "Weekly FPI net flow → INR Crores",
    rawValue:
      sig?.fpi_flow != null ? `${sig.fpi_flow.toFixed(0)} Cr` : undefined,
  }),
} as const;
