"use client";

import { useEffect, useState } from "react";
import { fmtBrier, fmtPctRaw } from "@/lib/track-record";
import type {
  SimulationResult,
  ValidationStats,
  VersionedRegimeBreakdownRow,
  VersionedRegimeCall,
} from "@/lib/supabase/queries";
import { VersionSelector } from "./VersionSelector";

interface BacktestData {
  versionedCalls: VersionedRegimeCall[];
  versionedBreakdown: VersionedRegimeBreakdownRow[];
  simulationResults: SimulationResult[];
  backtestT5: ValidationStats;
  backtestT20: ValidationStats;
  backtestT5ByPair: ValidationStats[];
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-surface)] px-8 py-12 text-center">
      <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-2">
        {message}
      </p>
      <p className="font-sans text-[13px] text-[var(--color-text-secondary)]">
        Data will populate when the pipeline completes the next run.
      </p>
    </div>
  );
}

function MiniEquityCurve({ data }: { data: { date: string; value: number }[] }) {
  if (data.length < 2) return null;
  const W = 300;
  const H = 80;
  const pad = 2;
  const chartW = W - pad * 2;
  const chartH = H - pad * 2;
  const values = data.map((d) => d.value);
  const minV = Math.min(...values);
  const maxV = Math.max(...values);
  const range = maxV - minV || 1;
  const pts = data.map((d, i) => {
    const x = pad + (i / (data.length - 1)) * chartW;
    const y = pad + chartH - ((d.value - minV) / range) * chartH;
    return `${x},${y}`;
  });
  return (
    <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label="Mini equity curve">
      <title>Mini Equity Curve</title>
      <rect width={W} height={H} fill="var(--color-void)" />
      <polyline points={pts.join(" ")} fill="none" stroke="var(--color-text-muted)" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function BacktestTabClient({
  versions,
  initialVersion,
}: {
  versions: string[];
  initialVersion: string;
}) {
  const [selectedVersion, setSelectedVersion] = useState(initialVersion);
  const [data, setData] = useState<BacktestData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch(`/api/backtest?version=${encodeURIComponent(selectedVersion)}`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load backtest data");
        return res.json();
      })
      .then((json: BacktestData) => {
        if (!cancelled) {
          setData(json);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedVersion]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4 mb-8 pb-4 border-b border-[var(--color-border)]">
          <span className="font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase">
            Backtested Track Record
          </span>
          <span className="text-[var(--color-border)]">·</span>
          <span className="font-mono text-[10px] text-[var(--color-text-muted)]">MODEL VERSION</span>
          <VersionSelector versions={versions} selectedVersion={selectedVersion} onChange={setSelectedVersion} />
        </div>
        <div className="animate-pulse space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-px bg-[var(--color-border)]">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="bg-[var(--color-surface)] p-4 h-20" />
            ))}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="border border-[var(--color-border)] bg-[var(--color-surface)] p-5 h-48" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div>
        <div className="flex items-center gap-4 mb-8 pb-4 border-b border-[var(--color-border)]">
          <span className="font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase">
            Backtested Track Record
          </span>
          <span className="text-[var(--color-border)]">·</span>
          <span className="font-mono text-[10px] text-[var(--color-text-muted)]">MODEL VERSION</span>
          <VersionSelector versions={versions} selectedVersion={selectedVersion} onChange={setSelectedVersion} />
        </div>
        <EmptyState message={error ?? "No backtested data available"} />
      </div>
    );
  }

  const {
    versionedCalls,
    versionedBreakdown,
    simulationResults,
    backtestT5,
    backtestT20,
    backtestT5ByPair,
  } = data;

  const hasData = versionedCalls.length > 0 || versionedBreakdown.length > 0;

  return (
    <div>
      {/* Version selector */}
      <div className="mb-8 pb-4 border-b border-[var(--color-border)] flex items-center gap-4">
        <span className="font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase">
          Backtested Track Record
        </span>
        <span className="text-[var(--color-border)]">·</span>
        <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
          MODEL VERSION
        </span>
        <VersionSelector
          versions={versions}
          selectedVersion={selectedVersion}
          onChange={setSelectedVersion}
        />
      </div>

      {!hasData ? (
        <EmptyState message="No backtested data available for this version" />
      ) : (
        <>
          {/* Summary metrics */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-px bg-[var(--color-border)] border border-[var(--color-border)] mb-10">
            <div className="bg-[var(--color-surface)] p-4">
              <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-1">T+5 WR</p>
              <p className="font-mono text-[clamp(16px,2vw,20px)] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">{fmtPctRaw(backtestT5.winRate)}</p>
            </div>
            <div className="bg-[var(--color-surface)] p-4">
              <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-1">T+5 BRIER</p>
              <p className="font-mono text-[clamp(16px,2vw,20px)] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">{fmtBrier(backtestT5.brierScore)}</p>
            </div>
            <div className="bg-[var(--color-surface)] p-4">
              <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-1">T+20 WR</p>
              <p className="font-mono text-[clamp(16px,2vw,20px)] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">{fmtPctRaw(backtestT20.winRate)}</p>
            </div>
            <div className="bg-[var(--color-surface)] p-4">
              <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-1">T+20 BRIER</p>
              <p className="font-mono text-[clamp(16px,2vw,20px)] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">{fmtBrier(backtestT20.brierScore)}</p>
            </div>
            <div className="bg-[var(--color-surface)] p-4">
              <p className="font-mono text-[9px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-1">TOTAL CALLS</p>
              <p className="font-mono text-[clamp(16px,2vw,20px)] font-medium text-[var(--color-text)] tracking-tight leading-none tabular-nums">{versionedCalls.length}</p>
            </div>
          </div>

          {/* Per-pair cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
            {["EURUSD", "USDJPY", "USDINR"].map((pair, idx) => {
              const pairCalls = versionedCalls.filter((c) => c.pair === pair);
              return (
                <div key={pair} className="border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
                  <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-3">
                    {pair.replace("EURUSD", "EUR/USD").replace("USDJPY", "USD/JPY").replace("USDINR", "USD/INR")}
                  </p>
                  <div className="grid grid-cols-2 gap-4 mb-3">
                    <div>
                      <p className="font-mono text-[9px] text-[var(--color-text-muted)]">T+5 WR</p>
                      <p className="font-mono text-[18px] text-[var(--color-text)] tabular-nums">{fmtPctRaw(backtestT5ByPair[idx]?.winRate)}</p>
                    </div>
                    <div>
                      <p className="font-mono text-[9px] text-[var(--color-text-muted)]">BRIER</p>
                      <p className="font-mono text-[18px] text-[var(--color-text)] tabular-nums">{fmtBrier(backtestT5ByPair[idx]?.brierScore)}</p>
                    </div>
                    <div>
                      <p className="font-mono text-[9px] text-[var(--color-text-muted)]">CALLS</p>
                      <p className="font-mono text-[18px] text-[var(--color-text)] tabular-nums">{backtestT5ByPair[idx]?.sampleSize ?? 0}</p>
                    </div>
                    <div>
                      <p className="font-mono text-[9px] text-[var(--color-text-muted)]">AVG RET</p>
                      <p className="font-mono text-[18px] text-[var(--color-text)] tabular-nums">
                        {(() => {
                          const v = backtestT5ByPair[idx]?.avgReturnBps;
                          if (v == null) return "—";
                          return `${v >= 0 ? "+" : ""}${v.toFixed(1)} bps`;
                        })()}
                      </p>
                    </div>
                  </div>
                  <MiniEquityCurve data={[]} />
                  <p className="font-mono text-[9px] text-[var(--color-text-muted)] mt-2">{pairCalls.length} calls in version</p>
                </div>
              );
            })}
          </div>

          {/* Full-width equity curve placeholder */}
          <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
            <div className="px-5 py-3 border-b border-[var(--color-border)]">
              <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">Cumulative T+20 Log-Return — Regime Shading</p>
            </div>
            <EmptyState message="Backtested equity curve pending" />
          </div>

          {/* Regime-conditioned matrix */}
          <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
            <div className="px-5 py-3 border-b border-[var(--color-border)]">
              <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">Regime-Conditioned Performance Matrix</p>
            </div>
            <div className="p-5">
              {versionedBreakdown.length === 0 ? (
                <p className="font-mono text-[10px] text-[var(--color-text-muted)] text-center py-8">NO REGIME BREAKDOWN DATA</p>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-[var(--color-border)]">
                  {versionedBreakdown.map((r) => (
                    <div key={`${r.pair}-${r.regime}`} className="bg-[var(--color-surface)] p-4">
                      <p className="font-mono text-[9px] text-[var(--color-text-muted)] uppercase">{r.pair} · {r.regime.replace(/_/g, " ")}</p>
                      <p className="font-mono text-[16px] text-[var(--color-text)] tabular-nums mt-1">{r.count}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Rolling 90-day metrics */}
          <div className="border border-[var(--color-border)] bg-[var(--color-surface)] mb-10">
            <div className="px-5 py-3 border-b border-[var(--color-border)]">
              <p className="font-mono text-[10px] tracking-[0.15em] text-[var(--color-text-muted)] uppercase">Rolling 90-Day Metrics</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse font-mono text-[11px]">
                <thead>
                  <tr className="border-b border-[var(--color-border)] bg-[var(--color-elevated)]">
                    <th className="px-4 py-2.5 text-left text-[9px] text-[var(--color-text-muted)] tracking-[0.15em] font-semibold uppercase">Pair</th>
                    <th className="px-4 py-2.5 text-left text-[9px] text-[var(--color-text-muted)] tracking-[0.15em] font-semibold uppercase">90D Win Rate</th>
                    <th className="px-4 py-2.5 text-left text-[9px] text-[var(--color-text-muted)] tracking-[0.15em] font-semibold uppercase">T+5 Brier</th>
                    <th className="px-4 py-2.5 text-left text-[9px] text-[var(--color-text-muted)] tracking-[0.15em] font-semibold uppercase">Sample</th>
                  </tr>
                </thead>
                <tbody>
                  {backtestT5ByPair.map((s, i) => (
                    <tr key={s.pair} className={`border-b border-[var(--color-border-subtle)] last:border-b-0 ${i % 2 === 1 ? "bg-[var(--color-elevated)]" : "bg-[var(--color-surface)]"}`}>
                      <th scope="row" className="px-4 py-2.5 text-[var(--color-text-secondary)] whitespace-nowrap font-medium text-left">{s.pair}</th>
                      <td className="px-4 py-2.5 text-[var(--color-text)] tabular-nums">{s.rolling90dAccuracy != null ? `${(s.rolling90dAccuracy * 100).toFixed(1)}%` : "—"}</td>
                      <td className="px-4 py-2.5 text-[var(--color-text)] tabular-nums">{s.brierScore != null ? s.brierScore.toFixed(3) : "—"}</td>
                      <td className="px-4 py-2.5 text-[var(--color-text-muted)] tabular-nums">n={s.sampleSize ?? 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Simulation results */}
          {simulationResults.length > 0 ? (
            <div className="border border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden mb-8">
              <div className="px-5 py-3 border-b border-[var(--color-border)]">
                <p className="font-mono text-[11px] text-[var(--color-text-muted)] tracking-wider">SIMULATION OUTPUT</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse font-mono text-[11px]">
                  <thead>
                    <tr className="border-b border-[var(--color-border)]">
                      <th className="px-4 py-2 text-left text-[var(--color-text-muted)]">PAIR</th>
                      <th className="px-4 py-2 text-left text-[var(--color-text-muted)]">METHOD</th>
                      <th className="px-4 py-2 text-right text-[var(--color-text-muted)]">SHARPE</th>
                      <th className="px-4 py-2 text-right text-[var(--color-text-muted)]">SORTINO</th>
                      <th className="px-4 py-2 text-right text-[var(--color-text-muted)]">WIN RATE</th>
                      <th className="px-4 py-2 text-right text-[var(--color-text-muted)]">TRADES</th>
                      <th className="px-4 py-2 text-right text-[var(--color-text-muted)]">TOTAL P&L</th>
                      <th className="px-4 py-2 text-right text-[var(--color-text-muted)]">MEAN BRIER</th>
                    </tr>
                  </thead>
                  <tbody>
                    {simulationResults.map((r) => (
                      <tr key={`${r.pair}-${r.sizingMethod}`} className="border-b border-[var(--color-border)] hover:bg-[var(--color-surface-hover)]">
                        <td className="px-4 py-2 text-[var(--color-text)]">{r.pair.replace("EURUSD", "EUR/USD").replace("USDJPY", "USD/JPY").replace("USDINR", "USD/INR")}</td>
                        <td className="px-4 py-2 text-[var(--color-text)]">{r.sizingMethod}</td>
                        <td className="px-4 py-2 text-right text-[var(--color-text)]">{r.sharpe != null ? r.sharpe.toFixed(2) : "—"}</td>
                        <td className="px-4 py-2 text-right text-[var(--color-text)]">{r.sortino != null ? r.sortino.toFixed(2) : "—"}</td>
                        <td className="px-4 py-2 text-right text-[var(--color-text)]">{r.winRate != null ? `${(r.winRate * 100).toFixed(1)}%` : "—"}</td>
                        <td className="px-4 py-2 text-right text-[var(--color-text)]">{r.nTrades ?? "—"}</td>
                        <td className={`px-4 py-2 text-right ${(r.totalPnl ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"}`}>{r.totalPnl != null ? `${r.totalPnl >= 0 ? "+" : ""}${r.totalPnl.toFixed(2)}` : "—"}</td>
                        <td className="px-4 py-2 text-right text-[var(--color-text)]">{r.meanBrier != null ? r.meanBrier.toFixed(3) : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="border border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-12 text-center mb-8">
              <p className="font-mono text-[11px] text-[var(--color-text-muted)] tracking-wider mb-2">NO SIMULATION DATA</p>
              <p className="font-sans text-[13px] text-[var(--color-text-secondary)]">Backtest simulation results for version {selectedVersion} are not yet available.</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
