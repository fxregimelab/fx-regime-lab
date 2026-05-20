"use client";

import { useState } from "react";

interface SignalFamily {
  key: string;
  label: string;
  weight: number;
  color: string;
  description: string;
  computation: string;
  source: string;
  sampleValue: number;
  sampleBias: "BULLISH" | "BEARISH" | "NEUTRAL";
}

const SIGNALS: SignalFamily[] = [
  {
    key: "rates",
    label: "Rate Differential",
    weight: 45,
    color: "#3b82f6",
    description:
      "2-year sovereign yield spread (US vs counterparty). The structural anchor of the composite score.",
    computation:
      "Rolling z-score of yield spread over a 252-day causal window with 90-day minimum. Uses population std.",
    source: "FRED DGS2, ECB data-api, MOF Japan",
    sampleValue: -0.45,
    sampleBias: "BEARISH",
  },
  {
    key: "cot",
    label: "COT Positioning",
    weight: 25,
    color: "#22c55e",
    description:
      "Commitment of Traders non-commercial net positions as 156-week percentile ranks.",
    computation:
      "CFTC weekly non-commercial net positions ranked over 156 weeks. Percentile π feeds crowding metrics phi_upper and phi_lower.",
    source: "CFTC Disaggregated weekly report",
    sampleValue: 0.62,
    sampleBias: "BULLISH",
  },
  {
    key: "vol",
    label: "Realized Volatility",
    weight: 20,
    color: "#a855f7",
    description:
      "21-day annualized realized vol scored against its 3-year empirical CDF. Gates entry at 88th percentile.",
    computation:
      "Annualized realized vol from daily spot returns vs trailing 756-session empirical distribution. Quantile q^σ_t blocks entry when > 0.88.",
    source: "Alpha Vantage spot data",
    sampleValue: -0.12,
    sampleBias: "NEUTRAL",
  },
  {
    key: "oi",
    label: "Open Interest",
    weight: 5,
    color: "#ec4899",
    description:
      "CME futures open-interest delta and price-alignment flag. Flags crowded positioning unwinds.",
    computation:
      "Daily OI change aligned with price direction. Crowded COT + 3-day shrinking OI triggers unwind flag.",
    source: "CME volume/OI daily CSV",
    sampleValue: -0.08,
    sampleBias: "NEUTRAL",
  },
  {
    key: "special",
    label: "Special Signal",
    weight: 5,
    color: "#eab308",
    description:
      "Cross-asset special factor. Varies by pair: VIX stress for JPY, oil+DXY for INR, Bund-BTP+ECB for EUR.",
    computation:
      "Pair-specific blend of cross-asset proxies normalized to [-1, +1]. EURUSD blends Bund-BTP spread (Italian sovereign stress) with ECB balance sheet YoY growth rate.",
    source: "Alpha Vantage, yfinance",
    sampleValue: 0.0,
    sampleBias: "NEUTRAL",
  },
];

function BiasBadge({ bias }: { bias: "BULLISH" | "BEARISH" | "NEUTRAL" }) {
  const colorClass =
    bias === "BULLISH"
      ? "text-[#22c55e]"
      : bias === "BEARISH"
        ? "text-[#ef4444]"
        : "text-[var(--color-text-muted)]";
  return (
    <span className={`font-mono text-xs font-semibold ${colorClass}`}>
      {bias}
    </span>
  );
}

function Mono({ children }: { children: React.ReactNode }) {
  return (
    <span className="font-mono text-sm text-[var(--color-text)]">
      {children}
    </span>
  );
}

export default function SignalDecomposition() {
  const [selected, setSelected] = useState<string | null>(null);

  const selectedSignal = SIGNALS.find((s) => s.key === selected);

  const compositeScore =
    Math.round(
      SIGNALS.reduce((sum, s) => sum + s.sampleValue * (s.weight / 100), 0) *
        100,
    ) / 100;

  const regimeLabel =
    compositeScore > 0.4
      ? "GROWTH_SURPRISE_USD"
      : compositeScore < -0.4
        ? "RISK_ON_DOLLAR_OFF"
        : "NEUTRAL";

  return (
    <div className="reveal mb-10">
      <h2 className="font-sans font-semibold text-xl text-[var(--color-text)] tracking-tight mb-4">
        Signal Decomposition
      </h2>
      <p className="font-sans text-[15px] text-[var(--color-text-secondary)] leading-[1.7] mb-6">
        The composite regime score is a weighted sum of five signal families.
        Weights vary by pair; shown below for EUR/USD. Click any segment to
        inspect its computation, source, and contribution.
      </p>

      {/* Stacked Bar */}
      <fieldset
        className="w-full h-10 flex rounded-[2px] overflow-hidden border border-[var(--color-border)] mb-6"
        aria-label="Signal weight breakdown"
      >
        {SIGNALS.map((signal) => {
          const isActive = selected === signal.key;
          return (
            <button
              key={signal.key}
              type="button"
              onClick={() => setSelected(isActive ? null : signal.key)}
              className="relative h-full flex items-center justify-center cursor-pointer transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-text)] focus-visible:ring-inset glow-hover"
              style={
                {
                  "--glow-color": `${signal.color}44`,
                  width: `${signal.weight}%`,
                  backgroundColor: signal.color,
                  opacity: selected === null || isActive ? 1 : 0.35,
                } as React.CSSProperties
              }
              aria-pressed={isActive}
              aria-label={`${signal.label}: ${signal.weight}% weight`}
              title={`${signal.label}: ${signal.weight}%`}
            >
              <span className="font-mono text-[10px] font-semibold text-white/90 truncate px-1 pointer-events-none select-none hidden sm:inline">
                {signal.weight >= 8 ? signal.label : ""}
              </span>
            </button>
          );
        })}
      </fieldset>

      {/* Legend (mobile-friendly) */}
      <div className="flex flex-wrap gap-x-4 gap-y-2 mb-6">
        {SIGNALS.map((signal) => (
          <button
            key={signal.key}
            type="button"
            onClick={() =>
              setSelected(selected === signal.key ? null : signal.key)
            }
            className={`flex items-center gap-1.5 cursor-pointer transition-all duration-200 glow-text ${
              selected === null || selected === signal.key
                ? "opacity-100"
                : "opacity-40"
            }`}
            style={
              { "--glow-color": `${signal.color}66` } as React.CSSProperties
            }
          >
            <span
              className="inline-block w-2.5 h-2.5 rounded-[1px] flex-shrink-0"
              style={{ backgroundColor: signal.color }}
            />
            <span className="font-mono text-[11px] text-[var(--color-text-secondary)]">
              {signal.label}{" "}
              <span className="text-[var(--color-text-muted)]">
                {signal.weight}%
              </span>
            </span>
          </button>
        ))}
      </div>

      {/* Detail Panel */}
      {selectedSignal && (
        <section
          className="border border-[var(--color-border)] bg-[var(--color-surface)] p-5 mb-6 animate-fade-in glow-active"
          style={
            {
              "--glow-color": `${selectedSignal.color}33`,
            } as React.CSSProperties
          }
          aria-label={`${selectedSignal.label} details`}
        >
          <div className="flex items-center gap-2 mb-3">
            <span
              className="inline-block w-3 h-3 rounded-[1px]"
              style={{ backgroundColor: selectedSignal.color }}
            />
            <h3 className="font-sans font-semibold text-lg text-[var(--color-text)]">
              {selectedSignal.label}
            </h3>
            <span className="font-mono text-xs text-[var(--color-text-muted)] ml-auto">
              WEIGHT {selectedSignal.weight}%
            </span>
          </div>
          <p className="font-sans text-[14px] text-[var(--color-text-secondary)] leading-relaxed mb-4">
            {selectedSignal.description}
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
            <div>
              <p className="font-mono text-[10px] tracking-[0.1em] text-[var(--color-text-muted)] uppercase mb-1">
                Computation
              </p>
              <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-relaxed">
                {selectedSignal.computation}
              </p>
            </div>
            <div>
              <p className="font-mono text-[10px] tracking-[0.1em] text-[var(--color-text-muted)] uppercase mb-1">
                Data Source
              </p>
              <p className="font-sans text-[13px] text-[var(--color-text-secondary)] leading-relaxed">
                {selectedSignal.source}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 pt-3 border-t border-[var(--color-border-subtle)]">
            <span className="font-mono text-[10px] tracking-[0.1em] text-[var(--color-text-muted)] uppercase">
              Sample Contribution
            </span>
            <Mono>
              {selectedSignal.sampleValue > 0 ? "+" : ""}
              {selectedSignal.sampleValue}
            </Mono>
            <span className="text-[var(--color-text-muted)]">·</span>
            <BiasBadge bias={selectedSignal.sampleBias} />
          </div>
        </section>
      )}

      {/* Live Example */}
      <div className="border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
        <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-4">
          Illustrative Example (Synthetic Data) — EUR/USD
        </p>

        <div className="flex flex-col gap-2 mb-4">
          {SIGNALS.map((signal) => (
            <div
              key={signal.key}
              className="flex items-center justify-between font-mono text-[12px]"
            >
              <div className="flex items-center gap-2">
                <span
                  className="inline-block w-2 h-2 rounded-[1px] flex-shrink-0"
                  style={{ backgroundColor: signal.color }}
                />
                <span className="text-[var(--color-text)] w-28">
                  {signal.label}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <BiasBadge bias={signal.sampleBias} />
                <span
                  className={`tabular-nums w-12 text-right ${
                    signal.sampleValue > 0
                      ? "text-[#22c55e]"
                      : signal.sampleValue < 0
                        ? "text-[#ef4444]"
                        : "text-[var(--color-text-muted)]"
                  }`}
                >
                  {signal.sampleValue > 0 ? "+" : ""}
                  {signal.sampleValue.toFixed(2)}
                </span>
                <span className="text-[var(--color-text-muted)] w-10 text-right">
                  ×{signal.weight}%
                </span>
                <span className="tabular-nums text-[var(--color-text)] w-14 text-right">
                  = {(signal.sampleValue * (signal.weight / 100)).toFixed(3)}
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="border-t border-[var(--color-border-subtle)] pt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div className="flex items-center gap-3">
            <span className="font-mono text-[10px] tracking-[0.1em] text-[var(--color-text-muted)] uppercase">
              Composite
            </span>
            <Mono>{compositeScore.toFixed(2)}</Mono>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-mono text-[10px] tracking-[0.1em] text-[var(--color-text-muted)] uppercase">
              Regime
            </span>
            <span className="font-mono text-sm font-semibold text-[var(--color-text)]">
              {regimeLabel}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
