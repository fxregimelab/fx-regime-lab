import { RegimeCard } from "@/components/regime/RegimeCard";
import { ConfidenceBar } from "@/components/ui/confidence-bar";
import { ResearchDisclaimer } from "@/components/ui/research-disclaimer";
import { Skeleton } from "@/components/ui/skeleton";
import { Sparkline } from "@/components/ui/sparkline";
import { fmt2, fmtInt, fmtPct } from "@/components/ui/utils";
import { PAIRS } from "@/lib/constants";
import {
  getHistoricalPrices,
  getHistoricalRegimeCalls,
  getLatestRegimeCalls,
  getLatestSignals,
  getPairValidationHistory,
  getPairValidationSummary,
} from "@/lib/supabase/queries";
import type {
  LatestRegimeCall,
  LatestSignal,
  PairValidationHistoryItem,
  PairValidationSummary,
} from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";
import Link from "next/link";
import { notFound } from "next/navigation";

interface PairDeskPageProps {
  params: Promise<{ pair: string }>;
}

export async function generateMetadata({ params }: PairDeskPageProps) {
  const { pair: pairSlug } = await params;
  const pairMeta = PAIRS.find((p) => p.urlSlug === pairSlug);
  return {
    title: pairMeta
      ? `${pairMeta.display} Desk | FX Regime Lab`
      : "FX Regime Lab",
  };
}

function getBias(
  call: LatestRegimeCall | undefined,
  composite: number,
): string {
  if (call?.rate_signal) return call.rate_signal;
  if (composite > 0.3) return "BULLISH";
  if (composite < -0.3) return "BEARISH";
  return "NEUTRAL";
}

function getInvalidation(
  bias: string,
  spot: number | null | undefined,
): string {
  if (!spot || bias === "NEUTRAL") return "—";
  const buffer = spot * 0.005;
  const inv = bias === "BULLISH" ? spot - buffer : spot + buffer;
  return inv.toFixed(4);
}

function getWatchlist(
  sig: LatestSignal | undefined,
  call: LatestRegimeCall | undefined,
): string[] {
  const items: string[] = [];
  if (sig?.realized_vol_20d != null && sig.realized_vol_20d > 8) {
    items.push("RVOL ELEVATED");
  }
  if (
    sig?.implied_vol_30d != null &&
    sig.realized_vol_20d != null &&
    sig.implied_vol_30d > sig.realized_vol_20d
  ) {
    items.push("IV PREM");
  }
  if (
    sig?.cot_percentile != null &&
    (sig.cot_percentile > 85 || sig.cot_percentile < 15)
  ) {
    items.push("COT EXTREME");
  }
  if (call?.rate_signal && call.rate_signal !== "NEUTRAL") {
    items.push("RATE DIVERGENCE");
  }
  if (items.length === 0) items.push("NO MAJOR ALERTS");
  return items;
}

function regimeDotColor(regime: string): string {
  if (regime.includes("STRENGTH")) return "var(--color-up)";
  if (regime.includes("WEAKNESS")) return "var(--color-down)";
  if (regime.includes("PRESSURE")) return "var(--color-down)";
  if (regime === "VOL_EXPANDING") return "var(--color-text-secondary)";
  return "var(--color-text-muted)";
}

function pseudoZScore(
  label: string,
  value: number | null | undefined,
  sig: LatestSignal | undefined,
): string {
  if (value == null) return "—";
  if (label === "Rate differential 2Y") {
    return (value / 0.75).toFixed(2);
  }
  if (label === "COT net position pctile") {
    return ((value - 50) / 16.67).toFixed(2);
  }
  if (label === "Signal composite") {
    return value.toFixed(2);
  }
  if (label === "Realized vol 20d" && sig?.realized_vol_5d != null) {
    const z = (value - sig.realized_vol_5d) / Math.max(value * 0.3, 0.5);
    return z.toFixed(2);
  }
  return "—";
}

function trendArrow(
  label: string,
  value: number | null | undefined,
  sig: LatestSignal | undefined,
): string {
  if (value == null) return "—";
  if (label === "Rate differential 2Y")
    return value > 0 ? "↑" : value < 0 ? "↓" : "→";
  if (label === "COT net position pctile") {
    return value > 60 ? "↑" : value < 40 ? "↓" : "→";
  }
  if (label === "Signal composite") {
    return value > 0.3 ? "↑" : value < -0.3 ? "↓" : "→";
  }
  if (label === "Realized vol 20d" && sig?.realized_vol_5d != null) {
    return value > sig.realized_vol_5d
      ? "↑"
      : value < sig.realized_vol_5d
        ? "↓"
        : "→";
  }
  if (label === "Implied vol 30d" && sig?.realized_vol_20d != null) {
    return value > sig.realized_vol_20d
      ? "↑"
      : value < sig.realized_vol_20d
        ? "↓"
        : "→";
  }
  return "—";
}

function arrowColor(arrow: string): string {
  if (arrow === "↑") return "var(--color-up)";
  if (arrow === "↓") return "var(--color-down)";
  return "var(--color-text-dim)";
}

const SIGNAL_ARCH = [
  { label: "RATE", weight: 40 },
  { label: "COT", weight: 30 },
  { label: "VOL", weight: 20 },
  { label: "OI", weight: 10 },
];

function OutcomeBadge({ outcome }: { outcome: string }) {
  if (outcome === "CORRECT")
    return (
      <span className="font-mono text-[10px] text-[var(--color-up)] font-bold">
        ✓ CORRECT
      </span>
    );
  if (outcome === "WRONG")
    return (
      <span className="font-mono text-[10px] text-[var(--color-down)] font-bold">
        ✗ WRONG
      </span>
    );
  return (
    <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
      {outcome}
    </span>
  );
}

function ValidationHistoryTable({
  rows,
}: {
  rows: PairValidationHistoryItem[];
}) {
  if (rows.length === 0) {
    return (
      <div className="px-5 py-6 text-center">
        <span className="font-mono text-[10px] text-[var(--color-text-muted)] tracking-wider">
          NO VALIDATION DATA FOR THIS PAIR
        </span>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse font-mono text-[11px]">
        <thead>
          <tr className="border-b border-[var(--color-border)] bg-[var(--color-elevated)]">
            {[
              "DATE",
              "PRED",
              "T+5 OUT",
              "T+5 RET",
              "T+5 BRIER",
              "T+20 OUT",
              "T+20 RET",
              "T+20 BRIER",
            ].map((h) => (
              <th
                key={h}
                scope="col"
                className="px-3 py-2 text-left text-[9px] text-[var(--color-text-muted)] tracking-[0.1em] font-semibold whitespace-nowrap"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr
              key={r.date}
              className={`border-b border-[var(--color-border-subtle)] last:border-b-0 ${i % 2 === 1 ? "bg-[var(--color-elevated)]" : "bg-[var(--color-surface)]"}`}
            >
              <td className="px-3 py-2 text-[var(--color-text-muted)] whitespace-nowrap">
                {r.date}
              </td>
              <td className="px-3 py-2 text-[var(--color-text-secondary)]">
                {r.predicted}
              </td>
              <td className="px-3 py-2">
                <OutcomeBadge outcome={r.t5Outcome} />
              </td>
              <td
                className={`px-3 py-2 tabular-nums ${r.t5ReturnBps != null && r.t5ReturnBps >= 0 ? "text-[var(--color-up)]" : "text-[var(--color-down)]"}`}
              >
                {r.t5ReturnBps != null
                  ? `${r.t5ReturnBps >= 0 ? "+" : ""}${r.t5ReturnBps.toFixed(1)}`
                  : "—"}
              </td>
              <td className="px-3 py-2 text-[var(--color-text)] tabular-nums">
                {r.t5Brier != null ? r.t5Brier.toFixed(3) : "—"}
              </td>
              <td className="px-3 py-2">
                <OutcomeBadge outcome={r.t20Outcome} />
              </td>
              <td
                className={`px-3 py-2 tabular-nums ${r.t20ReturnBps != null && r.t20ReturnBps >= 0 ? "text-[var(--color-up)]" : "text-[var(--color-down)]"}`}
              >
                {r.t20ReturnBps != null
                  ? `${r.t20ReturnBps >= 0 ? "+" : ""}${r.t20ReturnBps.toFixed(1)}`
                  : "—"}
              </td>
              <td className="px-3 py-2 text-[var(--color-text)] tabular-nums">
                {r.t20Brier != null ? r.t20Brier.toFixed(3) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ValidationStatsRow({
  stats,
}: {
  stats: PairValidationSummary | null;
}) {
  const tiles = [
    { label: "T+5 CAL", value: fmtPct(stats?.t5WinRate) },
    {
      label: "T+5 BRIER",
      value: stats?.t5Brier != null ? stats.t5Brier.toFixed(3) : "—",
    },
    { label: "T+5 SHARPE", value: fmt2(stats?.t5SharpeLike) },
    { label: "T+20 CAL", value: fmtPct(stats?.t20WinRate) },
    {
      label: "T+20 BRIER",
      value: stats?.t20Brier != null ? stats.t20Brier.toFixed(3) : "—",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-px bg-[var(--color-border)] border border-[var(--color-border)] mb-4">
      {tiles.map((t) => (
        <div key={t.label} className="bg-[var(--color-surface)] p-4">
          <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-1">
            {t.label}
          </p>
          <p className="font-mono text-[clamp(16px,2vw,20px)] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">
            {t.value}
          </p>
        </div>
      ))}
    </div>
  );
}

function ExecutionPanel({
  call,
  sig,
  pairLabel,
}: {
  call: LatestRegimeCall | undefined;
  sig: LatestSignal | undefined;
  pairLabel: string;
}) {
  const hasData =
    call?.entry_timing != null ||
    call?.position_size != null ||
    call?.stop_level != null ||
    sig?.realized_vol_rank != null;

  if (!hasData) return null;

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] px-5 py-3 mb-4">
      <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-2">
        HYPOTHETICAL — BACKTEST PARAMETERS
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div>
          <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
            ENTRY
          </span>
          <p className="font-mono text-[11px] text-[var(--color-text)] font-medium">
            {call?.entry_timing ?? "—"}
          </p>
        </div>
        <div>
          <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
            SIZE
          </span>
          <p className="font-mono text-[11px] text-[var(--color-text)] font-medium">
            {call?.position_size ?? "—"}
          </p>
        </div>
        <div>
          <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
            STOP
          </span>
          <p className="font-mono text-[11px] text-[var(--color-text)] font-medium tabular-nums">
            {call?.stop_level != null
              ? call.stop_level.toFixed(pairLabel === "USDJPY" ? 2 : 4)
              : "—"}
          </p>
        </div>
        <div>
          <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
            RVOL RANK
          </span>
          <p className="font-mono text-[11px] text-[var(--color-text)] font-medium tabular-nums">
            {fmtInt(sig?.realized_vol_rank)}
          </p>
        </div>
      </div>
    </div>
  );
}

export default async function PairDeskPage({ params }: PairDeskPageProps) {
  const { pair: pairSlug } = await params;
  const pairMeta = PAIRS.find((p) => p.urlSlug === pairSlug);
  if (!pairMeta) return notFound();

  const supabase = await createClient();

  const [calls, signals, history, prices, valStats, valHistory] =
    await Promise.all([
      getLatestRegimeCalls(supabase),
      getLatestSignals(supabase),
      getHistoricalRegimeCalls(supabase, pairMeta.label, 30),
      getHistoricalPrices(supabase, pairMeta.label, 30),
      getPairValidationSummary(supabase, pairMeta.label),
      getPairValidationHistory(supabase, pairMeta.label, 20),
    ]);

  const call = calls[pairMeta.label] as LatestRegimeCall | undefined;
  const sig = signals[pairMeta.label] as LatestSignal | undefined;
  const chg = sig?.day_change_pct;
  const composite = call?.signal_composite ?? 0;
  const compPct = Math.min(100, Math.max(0, ((composite + 2) / 4) * 100));

  const regimeAccent =
    call &&
    call.confidence != null && call.confidence >= 0.55 &&
    (call.regime.includes("STRENGTH") ||
      call.regime.includes("WEAKNESS") ||
      call.regime.includes("PRESSURE") ||
      call.regime === "VOL_EXPANDING");

  const cotPct = sig?.cot_percentile;
  const crowding =
    cotPct != null
      ? cotPct > 85
        ? "EXTREME HIGH"
        : cotPct < 15
          ? "EXTREME LOW"
          : null
      : null;

  const confidenceHistory = history.map((h) => h.confidence).reverse();
  const bias = getBias(call, composite);
  const invalidation = getInvalidation(bias, sig?.spot);
  const watchlist = getWatchlist(sig, call);

  const tableRows = [
    ["Rate differential 2Y", fmt2(sig?.rate_diff_2y), sig?.rate_diff_2y],
    [
      "COT net position pctile",
      pairMeta.label === "USDINR" ? "N/A" : fmtInt(cotPct ?? null),
      cotPct ?? null,
    ],
    ["Realized vol 20d", fmt2(sig?.realized_vol_20d), sig?.realized_vol_20d],
    ["Realized vol 5d", fmt2(sig?.realized_vol_5d), sig?.realized_vol_5d],
    [
      "Implied vol 30d",
      sig?.implied_vol_30d != null ? fmt2(sig.implied_vol_30d) : "—",
      sig?.implied_vol_30d ?? null,
    ],
    [
      "Signal composite",
      fmt2(call?.signal_composite),
      call?.signal_composite ?? null,
    ],
    [
      "Risk reversal 25d",
      sig?.risk_reversal_25d != null ? fmt2(sig.risk_reversal_25d) : "—",
      sig?.risk_reversal_25d ?? null,
    ],
    ...(pairMeta.label === "USDINR"
      ? [
          [
            "FPI flow (INR Cr)",
            sig?.fpi_flow != null ? fmt2(sig.fpi_flow) : "—",
            sig?.fpi_flow ?? null,
          ] as const,
        ]
      : []),
    [
      "Spot",
      sig?.spot?.toFixed(pairMeta.label === "USDJPY" ? 2 : 4) ?? "—",
      sig?.spot ?? null,
    ],
  ] as const;

  const priceSparkline = prices.map((p) => p.close);

  return (
    <div>
      {/* Research Disclaimer */}
      <ResearchDisclaimer />

      {/* Back navigation */}
      <div className="mb-4">
        <Link
          href="/terminal"
          className="font-mono text-[10px] text-[var(--color-text-muted)] tracking-wider hover:text-[var(--color-text)] transition-colors"
        >
          ← REGIME RESEARCH TERMINAL
        </Link>
      </div>

      {/* Top strip: spot + regime + confidence + composite */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-px mb-px bg-[var(--color-border)]">
        <div className="bg-[var(--color-elevated)] px-5 py-5">
          <p className="font-mono text-[9px] text-[var(--color-text-dim)] tracking-[0.15em] mb-2">
            SPOT PRICE
          </p>
          <p className="font-mono text-[28px] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">
            {sig?.spot?.toFixed(pairMeta.label === "USDJPY" ? 2 : 4) ?? "—"}
          </p>
          {chg != null && (
            <p
              className={`font-mono text-[11px] font-medium mt-2 ${
                chg >= 0 ? "text-[var(--color-up)]" : "text-[var(--color-down)]"
              }`}
            >
              {chg >= 0 ? "+" : ""}
              {chg.toFixed(2)}% today
            </p>
          )}
        </div>
        <div className="bg-[var(--color-elevated)] px-5 py-5">
          <p className="font-mono text-[9px] text-[var(--color-text-dim)] tracking-[0.15em] mb-2">
            REGIME
          </p>
          <p
            className={`font-mono text-[13px] font-bold tracking-wider leading-snug ${
              regimeAccent
                ? "text-[var(--color-text)]"
                : "text-[var(--color-text-secondary)]"
            }`}
          >
            {call?.regime ?? "—"}
          </p>
          <p className="font-mono text-[9px] text-[var(--color-text-muted)] mt-2 truncate">
            {call?.primary_driver?.slice(0, 50)}…
          </p>
        </div>
        <div className="bg-[var(--color-elevated)] px-5 py-5">
          <p className="font-mono text-[9px] text-[var(--color-text-dim)] tracking-[0.15em] mb-2">
            CONFIDENCE
          </p>
          <p
            className="font-mono text-[32px] font-medium tracking-tight leading-none"
            style={{ color: pairMeta.pairColor }}
          >
            {call?.confidence != null ? Math.min(100, Math.max(0, Math.round(call.confidence * 100))) : "—"}
            <span className="text-base text-[var(--color-text-dim)] font-normal">
              {call ? "%" : ""}
            </span>
          </p>
          <div className="mt-3">
            <ConfidenceBar
              value={call?.confidence}
              tone="dark"
              color={pairMeta.pairColor}
            />
          </div>
        </div>
        <div className="bg-[var(--color-elevated)] px-5 py-5">
          <p className="font-mono text-[9px] text-[var(--color-text-dim)] tracking-[0.15em] mb-2">
            SIGNAL COMPOSITE
          </p>
          <p
            className={`font-mono text-[32px] font-medium tracking-tight leading-none ${
              composite >= 0
                ? "text-[var(--color-up)]"
                : "text-[var(--color-down)]"
            }`}
          >
            {composite >= 0 ? "+" : ""}
            {fmt2(call?.signal_composite)}
          </p>
          <div className="mt-3 bg-[var(--color-surface)] h-[2px] relative">
            <div className="absolute left-1/2 top-[-1px] w-px h-[4px] bg-[var(--color-text-dim)]" />
            <div
              className="h-full"
              style={{
                width: `${compPct}%`,
                background:
                  composite >= 0 ? "var(--color-up)" : "var(--color-down)",
              }}
            />
          </div>
          <div className="flex justify-between mt-1.5">
            <span className="font-mono text-[8px] text-[var(--color-text-dim)]">
              BEAR -2
            </span>
            <span className="font-mono text-[8px] text-[var(--color-text-dim)]">
              BULL +2
            </span>
          </div>
        </div>
      </div>

      {/* Trader's TL;DR */}
      <div className="bg-[var(--color-elevated)] border border-[var(--color-border)] px-5 py-3.5 mb-px flex flex-wrap gap-x-6 gap-y-2 items-center">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[9px] text-[var(--color-text-dim)] tracking-[0.1em]">
            DIRECTIONAL BIAS
          </span>
          <span
            className="font-mono text-[11px] font-bold tracking-wider"
            style={{
              color:
                bias === "BULLISH"
                  ? "var(--color-up)"
                  : bias === "BEARISH"
                    ? "var(--color-down)"
                    : "var(--color-text-muted)",
            }}
          >
            {bias}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[9px] text-[var(--color-text-dim)] tracking-[0.1em]">
            DRIVER
          </span>
          <span className="font-mono text-[11px] text-[var(--color-text-secondary)] truncate max-w-[240px]">
            {call?.primary_driver ?? "—"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[9px] text-[var(--color-text-dim)] tracking-[0.1em]">
            MARCUS INVALIDATION
          </span>
          <span className="font-mono text-[11px] text-[var(--color-text)] tabular-nums">
            {invalidation}
          </span>
        </div>
        <div className="flex items-center gap-2 sm:ml-auto w-full sm:w-auto">
          <span className="font-mono text-[9px] text-[var(--color-text-dim)] tracking-[0.1em]">
            RISK FLAGS
          </span>
          <div className="flex gap-1.5">
            {watchlist.map((w) => (
              <span
                key={w}
                className="font-mono text-[9px] px-1.5 py-0.5 tracking-wider"
                style={{
                  color: "var(--color-text-muted)",
                  border: "1px solid var(--color-border)",
                  background: "var(--color-surface)",
                }}
              >
                {w}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Spot Price Sparkline */}
      {priceSparkline.length >= 2 && (
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] px-5 py-4 mb-4">
          <div className="flex justify-between items-center mb-2">
            <span className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-[0.15em]">
              SPOT PRICE (30D)
            </span>
            <span className="font-mono text-[9px] text-[var(--color-text-dim)]">
              {prices[0]?.date} → {prices[prices.length - 1]?.date}
            </span>
          </div>
          <div className="overflow-x-auto">
            <Sparkline
              data={priceSparkline}
              width={800}
              height={60}
              color={pairMeta.pairColor}
              fillOpacity={0.1}
            />
          </div>
        </div>
      )}

      {/* Signal Architecture Visualization */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] px-5 py-3 mb-4">
        <div className="flex justify-between items-center mb-2">
          <span className="font-mono text-[9px] text-[var(--color-text-dim)] tracking-[0.15em]">
            SIGNAL DECOMPOSITION
          </span>
          <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
            WEIGHTED COMPOSITE
          </span>
        </div>
        <div
          className="flex h-[6px] w-full overflow-hidden"
          style={{ background: "var(--color-void)" }}
        >
          {SIGNAL_ARCH.map((s) => (
            <div
              key={s.label}
              style={{
                width: `${s.weight}%`,
                background: `color-mix(in srgb, ${pairMeta.pairColor} 80%, transparent)`,
              }}
              title={`${s.label} ~${s.weight}%`}
            />
          ))}
        </div>
        <div className="flex justify-between mt-2">
          {SIGNAL_ARCH.map((s) => (
            <div key={s.label} className="flex items-center gap-1.5">
              <div
                className="w-2 h-2"
                style={{
                  background: `color-mix(in srgb, ${pairMeta.pairColor} 80%, transparent)`,
                }}
              />
              <span className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-wider">
                {s.label} {s.weight}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Signal chips */}
      <div className="bg-[var(--color-surface)] border border-[var(--color-border)] px-5 py-3 flex gap-2 items-center mb-4 flex-wrap">
        <span className="font-mono text-[9px] text-[var(--color-text-dim)] tracking-[0.1em] mr-1">
          REGIME FACTORS:
        </span>
        {[
          [
            "RATE",
            call?.rate_signal,
            call?.rate_signal === "BULLISH"
              ? "var(--color-up)"
              : call?.rate_signal === "BEARISH"
                ? "var(--color-down)"
                : "var(--color-text-muted)",
          ],
          [
            "COT",
            cotPct != null
              ? cotPct > 60
                ? "BULLISH"
                : cotPct < 40
                  ? "BEARISH"
                  : "NEUTRAL"
              : null,
            cotPct != null
              ? cotPct > 60
                ? "var(--color-up)"
                : cotPct < 40
                  ? "var(--color-down)"
                  : "var(--color-text-muted)"
              : "var(--color-text-muted)",
          ],
          [
            "VOL",
            sig?.realized_vol_20d != null
              ? sig.realized_vol_20d > 8
                ? "ELEVATED"
                : "NORMAL"
              : null,
            sig?.realized_vol_20d != null && sig.realized_vol_20d > 8
              ? "var(--color-text-secondary)"
              : "var(--color-up)",
          ],
          [
            "IV",
            sig?.implied_vol_30d != null
              ? sig.implied_vol_30d > (sig.realized_vol_20d ?? 0)
                ? "IV>RV"
                : "IV<RV"
              : null,
            sig?.implied_vol_30d != null &&
            sig.implied_vol_30d > (sig.realized_vol_20d ?? 0)
              ? "var(--color-text-secondary)"
              : "var(--color-text-muted)",
          ],
        ]
          .filter(([, dir]) => dir)
          .map(([lbl, dir, color]) => (
            <span
              key={lbl}
              className="font-mono text-[10px] px-2.5 py-1 font-medium tracking-wider"
              style={{
                color: color as string,
                border: `1px solid color-mix(in srgb, ${color as string} 20%, transparent)`,
                background: `color-mix(in srgb, ${color as string} 6%, transparent)`,
              }}
            >
              {lbl}: {dir}
            </span>
          ))}
        {crowding && (
          <span
            className="font-mono text-[10px] px-2.5 py-1 font-medium"
            style={{
              color: "var(--color-text-secondary)",
              border:
                "1px solid color-mix(in srgb, var(--color-text-secondary) 20%, transparent)",
              background:
                "color-mix(in srgb, var(--color-text-secondary) 6%, transparent)",
            }}
          >
            COT: {crowding}
          </span>
        )}
        <span className="ml-auto font-mono text-[9px] text-[var(--color-text-dim)]">
          {call?.date ?? sig?.date ?? "—"}
        </span>
      </div>

      {/* Validation Stats */}
      <ValidationStatsRow stats={valStats} />

      {/* Execution Panel */}
      <ExecutionPanel call={call} sig={sig} pairLabel={pairMeta.label} />

      {/* Main grid: signals table + sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-px bg-[var(--color-border)]">
        {/* Left panel */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)]">
          <div className="px-4 py-3 border-b border-[var(--color-border-subtle)] bg-[var(--color-surface)]">
            <span className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-[0.15em]">
              SIGNALS TABLE
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse font-mono">
              <thead>
                <tr className="border-b border-[var(--color-border-subtle)] bg-[var(--color-void)]">
                <th
                  scope="col"
                  className="px-4 py-2 text-left text-[9px] text-[var(--color-text-dim)] tracking-[0.1em] font-normal"
                >
                  SIGNAL
                </th>
                <th
                  scope="col"
                  className="px-4 py-2 text-left text-[9px] text-[var(--color-text-dim)] tracking-[0.1em] font-normal"
                >
                  VALUE
                </th>
                <th
                  scope="col"
                  className="px-4 py-2 text-left text-[9px] text-[var(--color-text-dim)] tracking-[0.1em] font-normal"
                >
                  SCORE
                </th>
                <th
                  scope="col"
                  className="px-4 py-2 text-left text-[9px] text-[var(--color-text-dim)] tracking-[0.1em] font-normal"
                >
                  TREND
                </th>
              </tr>
            </thead>
            <tbody>
              {tableRows.map(([label, value, raw], i) => {
                const arrow = trendArrow(label, raw, sig);
                const z = pseudoZScore(label, raw, sig);
                return (
                  <tr
                    key={label}
                    className="border-b border-[var(--color-border-subtle)]"
                    style={{
                      background:
                        i % 2 === 0
                          ? "var(--color-void)"
                          : "var(--color-surface)",
                    }}
                  >
                    <td className="px-4 py-3 text-[11px] text-[var(--color-text-muted)]">
                      {label}
                    </td>
                    <td className="px-4 py-3 text-[13px] text-[var(--color-text)] font-medium text-left tabular-nums">
                      {value}
                    </td>
                    <td className="px-4 py-3 text-[11px] text-[var(--color-text-secondary)] tabular-nums">
                      {z}
                    </td>
                    <td
                      className="px-4 py-3 text-[13px] font-medium"
                      style={{ color: arrowColor(arrow) }}
                    >
                      {arrow}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          </div>
          {call?.primary_driver && (
            <div className="px-4 py-3 border-t border-[var(--color-border-subtle)] bg-[var(--color-surface)]">
              <span className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-[0.1em] mr-3">
                PRIMARY DRIVER
              </span>
              <span className="font-mono text-[11px] text-[var(--color-text-secondary)]">
                {call.primary_driver}
              </span>
            </div>
          )}

          {/* Validation History Table */}
          <div className="border-t border-[var(--color-border)]">
            <div className="px-4 py-3 border-b border-[var(--color-border-subtle)] bg-[var(--color-surface)]">
              <span className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-[0.15em]">
                VALIDATION HISTORY (LAST 20)
              </span>
            </div>
            <ValidationHistoryTable rows={valHistory} />
          </div>
        </div>

        {/* Right sidebar */}
        <div className="flex flex-col gap-px bg-[var(--color-border)]">
          {/* Other Desks */}
          <div className="bg-[var(--color-surface)] p-4 border border-[var(--color-border)]">
            <p className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-[0.15em] mb-3">
              OTHER DESKS
            </p>
            <div className="flex flex-col gap-px">
              {PAIRS.filter((p) => p.label !== pairMeta.label).map((p) => (
                <RegimeCard
                  key={p.label}
                  call={
                    (calls[p.label] as LatestRegimeCall | undefined) ?? null
                  }
                  signals={
                    (signals[p.label] as LatestSignal | undefined) ?? null
                  }
                  pairDisplay={p.display}
                />
              ))}
            </div>
          </div>

          {/* Regime History */}
          <div className="bg-[var(--color-surface)] p-4 border border-[var(--color-border)]">
            <p className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-[0.15em] mb-3">
              REGIME HISTORY (7D)
            </p>
            {history.slice(0, 7).map((h) => (
              <div
                key={h.date}
                className="flex justify-between items-center py-1.5 border-b border-[var(--color-border-subtle)] last:border-b-0"
              >
                <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
                  {h.date}
                </span>
                <span className="font-mono text-[10px] text-[var(--color-text)] font-medium">
                  {h.regime}
                </span>
                <span
                  className="font-mono text-[10px] font-medium"
                  style={{ color: pairMeta.pairColor }}
                >
                  {Math.min(100, Math.max(0, Math.round(h.confidence * 100)))}%
                </span>
              </div>
            ))}
          </div>

          {/* Confidence Trend Sparkline */}
          <div className="bg-[var(--color-surface)] p-4 border border-[var(--color-border)]">
            <p className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-[0.15em] mb-3">
              CONFIDENCE TREND (14D)
            </p>
            <Sparkline
              data={confidenceHistory.slice(-14)}
              width={260}
              height={70}
              color={pairMeta.pairColor}
              fillOpacity={0.15}
            />
            <div className="flex justify-between mt-2">
              <span className="font-mono text-[9px] text-[var(--color-text-dim)]">
                {history.slice(-14)[0]?.date ?? ""}
              </span>
              <span className="font-mono text-[9px] text-[var(--color-text-dim)]">
                {history[0]?.date ?? ""}
              </span>
            </div>
          </div>

          {/* 30-Day Regime Timeline */}
          <div className="bg-[var(--color-surface)] p-4 border border-[var(--color-border)]">
            <p className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-[0.15em] mb-3">
              REGIME TIMELINE (30D)
            </p>
            <div className="flex flex-wrap gap-[3px]">
              {history
                .slice(0, 30)
                .reverse()
                .map((h) => (
                  <div key={h.date} className="group relative">
                    <div
                      className="w-[9px] h-[9px]"
                      style={{
                        background: regimeDotColor(h.regime),
                        opacity: 0.85,
                      }}
                      title={`${h.date}: ${h.regime} (${Math.min(100, Math.max(0, Math.round(h.confidence * 100)))}%)`}
                    />
                    {/* Tooltip on hover */}
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block z-10 whitespace-nowrap">
                      <div className="bg-[var(--color-elevated)] border border-[var(--color-border)] px-2 py-1">
                        <span className="font-mono text-[9px] text-[var(--color-text-secondary)]">
                          {h.date} · {h.regime}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
            <div className="flex justify-between mt-3">
              <span className="font-mono text-[8px] text-[var(--color-text-dim)]">
                {history.slice(0, 30).reverse()[0]?.date ?? ""}
              </span>
              <span className="font-mono text-[8px] text-[var(--color-text-dim)]">
                {history[0]?.date ?? ""}
              </span>
            </div>
            {/* Legend */}
            <div className="flex gap-3 mt-2">
              {[
                ["STRENGTH", "var(--color-up)"],
                ["WEAKNESS", "var(--color-down)"],
                ["VOL", "var(--color-text-secondary)"],
                ["OTHER", "var(--color-text-muted)"],
              ].map(([lbl, col]) => (
                <div key={lbl} className="flex items-center gap-1">
                  <div
                    className="w-[6px] h-[6px]"
                    style={{ background: col }}
                  />
                  <span className="font-mono text-[8px] text-[var(--color-text-dim)]">
                    {lbl}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
