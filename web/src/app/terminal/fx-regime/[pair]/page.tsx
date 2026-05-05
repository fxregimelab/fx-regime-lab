import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import {
  getLatestRegimeCalls,
  getLatestSignals,
  getHistoricalRegimeCalls,
  getSignalHistory,
} from "@/lib/supabase/queries";
import { RegimeCard } from "@/components/regime/RegimeCard";
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

  return (
    <div>
      {/* Top strip: spot + regime + confidence + composite */}
      <div
        className="grid gap-0.5 mb-0.5 border border-terminal-border"
        style={{ gridTemplateColumns: "repeat(4, 1fr)" }}
      >
        <div className="bg-[#0d0d0d] px-5 py-4 border-r border-[#1a1a1a]">
          <p className="font-mono text-[9px] text-terminal-dim tracking-[0.12em] mb-1.5">
            SPOT PRICE
          </p>
          <p className="font-mono text-[30px] font-bold text-white tracking-tight leading-none">
            {sig?.spot?.toFixed(pairMeta.label === "USDJPY" ? 2 : 4) ?? "—"}
          </p>
          {chg != null && (
            <p
              className={`font-mono text-[11px] font-bold mt-1.5 ${
                chg >= 0 ? "text-bullish" : "text-bearish"
              }`}
            >
              {chg >= 0 ? "+" : ""}
              {chg.toFixed(2)}% today
            </p>
          )}
        </div>
        <div className="bg-[#0d0d0d] px-5 py-4 border-r border-[#1a1a1a]">
          <p className="font-mono text-[9px] text-terminal-dim tracking-[0.12em] mb-1.5">
            REGIME
          </p>
          <p
            className={`font-mono text-[13px] font-bold tracking-wider leading-snug ${
              regimeAccent ? "text-brand-accent" : "text-white"
            }`}
          >
            {call?.regime ?? "—"}
          </p>
          <p className="font-mono text-[9px] text-terminal-muted mt-2">
            {call?.primary_driver?.slice(0, 45)}…
          </p>
        </div>
        <div className="bg-[#0d0d0d] px-5 py-4 border-r border-[#1a1a1a]">
          <p className="font-mono text-[9px] text-terminal-dim tracking-[0.12em] mb-1.5">
            CONFIDENCE
          </p>
          <p className="font-mono text-[36px] font-bold tracking-tight leading-none" style={{ color: pairMeta.pairColor }}>
            {call ? Math.round(call.confidence * 100) : "—"}
            <span className="text-base text-[#444] font-normal">
              {call ? "%" : ""}
            </span>
          </p>
          <div className="mt-2">
            <ConfidenceBar value={call?.confidence} tone="dark" color={pairMeta.pairColor} />
          </div>
        </div>
        <div className="bg-[#0d0d0d] px-5 py-4">
          <p className="font-mono text-[9px] text-terminal-dim tracking-[0.12em] mb-1.5">
            COMPOSITE SCORE
          </p>
          <p
            className={`font-mono text-[36px] font-bold tracking-tight leading-none ${
              composite >= 0 ? "text-bullish" : "text-bearish"
            }`}
          >
            {composite >= 0 ? "+" : ""}
            {fmt2(call?.signal_composite)}
          </p>
          <div className="mt-2 bg-[#1a1a1a] h-[3px] relative">
            <div className="absolute left-1/2 top-[-1px] w-px h-[5px] bg-[#333]" />
            <div
              className="h-full"
              style={{
                width: `${compPct}%`,
                background: composite >= 0 ? "#4ade80" : "#f87171",
              }}
            />
          </div>
          <div className="flex justify-between mt-1">
            <span className="font-mono text-[8px] text-[#333]">BEAR -2</span>
            <span className="font-mono text-[8px] text-[#333]">BULL +2</span>
          </div>
        </div>
      </div>

      {/* Signal chips */}
      <div className="bg-[#0c0c0c] border border-[#1a1a1a] border-t-0 px-5 py-2.5 flex gap-2 items-center mb-4 flex-wrap">
        <span className="font-mono text-[9px] text-[#666] tracking-[0.1em] mr-1">
          SIGNALS:
        </span>
        {[
          [
            "RATE",
            call?.rate_signal,
            call?.rate_signal === "BULLISH"
              ? "#4ade80"
              : call?.rate_signal === "BEARISH"
                ? "#f87171"
                : "#888",
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
                ? "#4ade80"
                : cotPct < 40
                  ? "#f87171"
                  : "#888"
              : "#888",
          ],
          [
            "VOL",
            sig?.realized_vol_20d != null
              ? sig.realized_vol_20d > 8
                ? "ELEVATED"
                : "NORMAL"
              : null,
            sig?.realized_vol_20d != null && sig.realized_vol_20d > 8
              ? "#fbbf24"
              : "#4ade80",
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
              ? "#fbbf24"
              : "#888",
          ],
        ]
          .filter(([, dir]) => dir)
          .map(([lbl, dir, color]) => (
            <span
              key={lbl}
              className="font-mono text-[10px] px-2.5 py-1 font-bold tracking-wider"
              style={{
                color: color as string,
                border: `1px solid ${(color as string)}30`,
                background: `${(color as string)}10`,
              }}
            >
              {lbl}: {dir}
            </span>
          ))}
        {crowding && (
          <span
            className="font-mono text-[10px] px-2.5 py-1 font-bold"
            style={{
              color: "#fbbf24",
              border: "1px solid #fbbf2430",
              background: "#fbbf2410",
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
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-0.5">
        {/* Left panel */}
        <div className="border border-[#1a1a1a]">
          <div className="px-4 py-3 border-b border-[#1a1a1a] bg-[#0c0c0c]">
            <span className="font-mono text-[9px] text-[#777] tracking-[0.12em]">
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
                  className="border-b border-[#0f0f0f]"
                  style={{
                    background: i % 2 === 0 ? "#0a0a0a" : "#0c0c0c",
                  }}
                >
                  <td className="px-4 py-3 text-[11px] text-[#aaa]">{label}</td>
                  <td className="px-4 py-3 text-[13px] text-white font-bold text-left">
                    {value}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {call?.primary_driver && (
            <div className="px-4 py-3 border-t border-[#141414] bg-[#0c0c0c]">
              <span className="font-mono text-[9px] text-[#777] tracking-[0.1em] mr-3">
                PRIMARY DRIVER
              </span>
              <span className="font-mono text-[11px] text-[#bbb]">
                {call.primary_driver}
              </span>
            </div>
          )}
        </div>

        {/* Right sidebar */}
        <div className="flex flex-col gap-0.5">
          {/* Other Desks */}
          <div className="border border-[#1a1a1a] bg-[#0c0c0c] p-3">
            <p className="font-mono text-[9px] text-[#777] tracking-[0.12em] mb-2.5">
              OTHER DESKS
            </p>
            <div className="flex flex-col gap-0.5">
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

          {/* History mini-table */}
          <div className="border border-[#1a1a1a] bg-[#0c0c0c] p-3">
            <p className="font-mono text-[9px] text-[#777] tracking-[0.12em] mb-2.5">
              REGIME HISTORY (7D)
            </p>
            {history.slice(0, 7).map((h, i) => (
              <div
                key={i}
                className="flex justify-between items-center py-1.5 border-b border-[#111] last:border-b-0"
              >
                <span className="font-mono text-[10px] text-[#999]">
                  {h.date}
                </span>
                <span className="font-mono text-[10px] text-[#e0e0e0] font-bold">
                  {h.regime}
                </span>
                <span
                  className="font-mono text-[10px] font-bold"
                  style={{ color: pairMeta.pairColor }}
                >
                  {Math.round(h.confidence * 100)}%
                </span>
              </div>
            ))}
          </div>

          {/* Signal sparkline placeholder */}
          <div className="border border-[#1a1a1a] bg-[#0c0c0c] p-3">
            <p className="font-mono text-[9px] text-[#777] tracking-[0.12em] mb-2">
              CONFIDENCE TREND
            </p>
            <div className="h-16 flex items-end gap-1">
              {history
                .slice(0, 14)
                .reverse()
                .map((h, i) => (
                  <div
                    key={i}
                    className="flex-1 rounded-sm"
                    style={{
                      height: `${h.confidence * 100}%`,
                      background: pairMeta.pairColor,
                      opacity: 0.7,
                      minHeight: "4px",
                    }}
                  />
                ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
