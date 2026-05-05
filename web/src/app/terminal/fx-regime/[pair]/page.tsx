import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import {
  getLatestRegimeCalls,
  getLatestSignals,
  getHistoricalRegimeCalls,
} from "@/lib/supabase/queries";
import { RegimeCard } from "@/components/regime/RegimeCard";
import { Sparkline } from "@/components/ui/sparkline";
import { ConfidenceBar } from "@/components/ui/confidence-bar";
import { fmt2, fmtInt, fmtPct } from "@/components/ui/utils";
import { PAIRS } from "@/lib/constants";
import type { LatestRegimeCall, LatestSignal } from "@/lib/supabase/queries";

interface PairDeskPageProps {
  params: Promise<{ pair: string }>;
}

export default async function PairDeskPage({ params }: PairDeskPageProps) {
  const { pair: pairSlug } = await params;
  const pairMeta = PAIRS.find((p) => p.urlSlug === pairSlug);
  if (!pairMeta) return notFound();

  const supabase = await createClient();

  const [calls, signals, history] = await Promise.all([
    getLatestRegimeCalls(supabase),
    getLatestSignals(supabase),
    getHistoricalRegimeCalls(supabase, pairMeta.label, 30),
  ]);

  const call = calls[pairMeta.label] as LatestRegimeCall | undefined;
  const sig = signals[pairMeta.label] as LatestSignal | undefined;
  const chg = sig?.day_change_pct;
  const composite = call?.signal_composite ?? 0;
  const compPct = Math.min(100, Math.max(0, ((composite + 2) / 4) * 100));

  const regimeAccent =
    call &&
    call.confidence >= 0.55 &&
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

  return (
    <div>
      {/* Top strip: spot + regime + confidence + composite */}
      <div className="grid gap-px mb-px bg-terminal-border" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
        <div className="bg-terminal-elevated px-5 py-5">
          <p className="font-mono text-[9px] text-terminal-dim tracking-[0.15em] mb-2">
            SPOT PRICE
          </p>
          <p className="font-mono text-[28px] font-medium text-white tracking-tight leading-none tabular-nums">
            {sig?.spot?.toFixed(pairMeta.label === "USDJPY" ? 2 : 4) ?? "—"}
          </p>
          {chg != null && (
            <p
              className={`font-mono text-[11px] font-medium mt-2 ${
                chg >= 0 ? "text-[#7a9e7a]" : "text-[#b87a7a]"
              }`}
            >
              {chg >= 0 ? "+" : ""}
              {chg.toFixed(2)}% today
            </p>
          )}
        </div>
        <div className="bg-terminal-elevated px-5 py-5">
          <p className="font-mono text-[9px] text-terminal-dim tracking-[0.15em] mb-2">
            REGIME
          </p>
          <p
            className={`font-mono text-[13px] font-bold tracking-wider leading-snug ${
              regimeAccent ? "text-terminal-text" : "text-[#a0a0a0]"
            }`}
          >
            {call?.regime ?? "—"}
          </p>
          <p className="font-mono text-[9px] text-terminal-muted mt-2 truncate">
            {call?.primary_driver?.slice(0, 50)}…
          </p>
        </div>
        <div className="bg-terminal-elevated px-5 py-5">
          <p className="font-mono text-[9px] text-terminal-dim tracking-[0.15em] mb-2">
            CONFIDENCE
          </p>
          <p className="font-mono text-[32px] font-medium tracking-tight leading-none" style={{ color: pairMeta.pairColor }}>
            {call ? Math.round(call.confidence * 100) : "—"}
            <span className="text-base text-terminal-dim font-normal">
              {call ? "%" : ""}
            </span>
          </p>
          <div className="mt-3">
            <ConfidenceBar value={call?.confidence} tone="dark" color={pairMeta.pairColor} />
          </div>
        </div>
        <div className="bg-terminal-elevated px-5 py-5">
          <p className="font-mono text-[9px] text-terminal-dim tracking-[0.15em] mb-2">
            COMPOSITE
          </p>
          <p
            className={`font-mono text-[32px] font-medium tracking-tight leading-none ${
              composite >= 0 ? "text-[#7a9e7a]" : "text-[#b87a7a]"
            }`}
          >
            {composite >= 0 ? "+" : ""}
            {fmt2(call?.signal_composite)}
          </p>
          <div className="mt-3 bg-[#1a1a1a] h-[2px] relative">
            <div className="absolute left-1/2 top-[-1px] w-px h-[4px] bg-[#333]" />
            <div
              className="h-full"
              style={{
                width: `${compPct}%`,
                background: composite >= 0 ? "#7a9e7a" : "#b87a7a",
              }}
            />
          </div>
          <div className="flex justify-between mt-1.5">
            <span className="font-mono text-[8px] text-[#333]">BEAR -2</span>
            <span className="font-mono text-[8px] text-[#333]">BULL +2</span>
          </div>
        </div>
      </div>

      {/* Signal chips */}
      <div className="bg-terminal-surface border border-terminal-border px-5 py-3 flex gap-2 items-center mb-4 flex-wrap">
        <span className="font-mono text-[9px] text-terminal-dim tracking-[0.1em] mr-1">
          SIGNALS:
        </span>
        {[
          [
            "RATE",
            call?.rate_signal,
            call?.rate_signal === "BULLISH"
              ? "#7a9e7a"
              : call?.rate_signal === "BEARISH"
                ? "#b87a7a"
                : "#666",
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
                ? "#7a9e7a"
                : cotPct < 40
                  ? "#b87a7a"
                  : "#666"
              : "#666",
          ],
          [
            "VOL",
            sig?.realized_vol_20d != null
              ? sig.realized_vol_20d > 8
                ? "ELEVATED"
                : "NORMAL"
              : null,
            sig?.realized_vol_20d != null && sig.realized_vol_20d > 8
              ? "#a8947a"
              : "#7a9e7a",
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
              ? "#a8947a"
              : "#666",
          ],
        ]
          .filter(([, dir]) => dir)
          .map(([lbl, dir, color]) => (
            <span
              key={lbl}
              className="font-mono text-[10px] px-2.5 py-1 font-medium tracking-wider"
              style={{
                color: color as string,
                border: `1px solid ${(color as string)}25`,
                background: `${(color as string)}08`,
              }}
            >
              {lbl}: {dir}
            </span>
          ))}
        {crowding && (
          <span
            className="font-mono text-[10px] px-2.5 py-1 font-medium"
            style={{
              color: "#a8947a",
              border: "1px solid #a8947a25",
              background: "#a8947a08",
            }}
          >
            COT: {crowding}
          </span>
        )}
        <span className="ml-auto font-mono text-[9px] text-[#333]">
          {new Date().toISOString().slice(0, 10)}
        </span>
      </div>

      {/* Main grid: signals table + sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-px bg-terminal-border">
        {/* Left panel */}
        <div className="bg-terminal-surface border border-terminal-border">
          <div className="px-4 py-3 border-b border-terminal-border-subtle bg-terminal-surface">
            <span className="font-mono text-[9px] text-terminal-muted tracking-[0.15em]">
              SIGNALS TABLE
            </span>
          </div>
          <table className="w-full border-collapse font-mono">
            <tbody>
              {[
                ["Rate differential 2Y", fmt2(sig?.rate_diff_2y)],
                ["COT net position pctile", fmtInt(cotPct ?? null)],
                ["Realized vol 20d", fmt2(sig?.realized_vol_20d)],
                ["Realized vol 5d", fmt2(sig?.realized_vol_5d)],
                ["Implied vol 30d", sig?.implied_vol_30d != null ? fmt2(sig.implied_vol_30d) : "—"],
                ["Signal composite", fmt2(call?.signal_composite)],
                ["Spot", sig?.spot?.toFixed(pairMeta.label === "USDJPY" ? 2 : 4) ?? "—"],
              ].map(([label, value], i) => (
                <tr
                  key={label}
                  className="border-b border-terminal-border-subtle"
                  style={{
                    background: i % 2 === 0 ? "#0a0a0a" : "#0c0c0c",
                  }}
                >
                  <td className="px-4 py-3 text-[11px] text-terminal-muted">{label}</td>
                  <td className="px-4 py-3 text-[13px] text-white font-medium text-left tabular-nums">
                    {value}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {call?.primary_driver && (
            <div className="px-4 py-3 border-t border-terminal-border-subtle bg-terminal-surface">
              <span className="font-mono text-[9px] text-terminal-muted tracking-[0.1em] mr-3">
                PRIMARY DRIVER
              </span>
              <span className="font-mono text-[11px] text-[#bbb]">
                {call.primary_driver}
              </span>
            </div>
          )}
        </div>

        {/* Right sidebar */}
        <div className="flex flex-col gap-px bg-terminal-border">
          {/* Other Desks */}
          <div className="bg-terminal-surface p-4 border border-terminal-border">
            <p className="font-mono text-[9px] text-terminal-muted tracking-[0.15em] mb-3">
              OTHER DESKS
            </p>
            <div className="flex flex-col gap-px">
              {PAIRS.filter((p) => p.label !== pairMeta.label).map((p) => (
                <RegimeCard
                  key={p.label}
                  call={(calls[p.label] as LatestRegimeCall | undefined) ?? null}
                  signals={(signals[p.label] as LatestSignal | undefined) ?? null}
                  pairDisplay={p.display}
                />
              ))}
            </div>
          </div>

          {/* Regime History */}
          <div className="bg-terminal-surface p-4 border border-terminal-border">
            <p className="font-mono text-[9px] text-terminal-muted tracking-[0.15em] mb-3">
              REGIME HISTORY (7D)
            </p>
            {history.slice(0, 7).map((h, i) => (
              <div
                key={i}
                className="flex justify-between items-center py-1.5 border-b border-terminal-border-subtle last:border-b-0"
              >
                <span className="font-mono text-[10px] text-terminal-muted">
                  {h.date}
                </span>
                <span className="font-mono text-[10px] text-terminal-text font-medium">
                  {h.regime}
                </span>
                <span
                  className="font-mono text-[10px] font-medium"
                  style={{ color: pairMeta.pairColor }}
                >
                  {Math.round(h.confidence * 100)}%
                </span>
              </div>
            ))}
          </div>

          {/* Confidence Trend Sparkline */}
          <div className="bg-terminal-surface p-4 border border-terminal-border">
            <p className="font-mono text-[9px] text-terminal-muted tracking-[0.15em] mb-3">
              CONFIDENCE TREND (14D)
            </p>
            <Sparkline
              data={confidenceHistory.slice(-14)}
              width={260}
              height={50}
              color={pairMeta.pairColor}
              fillOpacity={0.15}
            />
            <div className="flex justify-between mt-2">
              <span className="font-mono text-[9px] text-terminal-dim">
                {history.slice(-14)[0]?.date ?? ""}
              </span>
              <span className="font-mono text-[9px] text-terminal-dim">
                {history[0]?.date ?? ""}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
