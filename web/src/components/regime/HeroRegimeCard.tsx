import { ConfidenceBar } from "@/components/ui/confidence-bar";
import { fmt2, fmtInt } from "@/components/ui/utils";
import type { LatestRegimeCall, LatestSignal } from "@/lib/supabase/queries";

interface HeroRegimeCardProps {
  call?: LatestRegimeCall | null;
  signals?: LatestSignal | null;
}

export function HeroRegimeCard({ call, signals }: HeroRegimeCardProps) {
  const pct = call ? Math.round(call.confidence * 100) : null;
  const chg = signals?.day_change_pct;
  const pairColor = "#4BA3E3";

  return (
    <div className="bg-terminal-bg border border-terminal-border">
      {/* Card header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#1a1a1a]">
        <div className="flex items-center gap-2">
          <span
            className="w-2 h-2 inline-block flex-shrink-0"
            style={{ background: pairColor }}
          />
          <span
            className="font-mono text-xs font-bold tracking-wider"
            style={{ color: pairColor }}
          >
            EUR/USD
          </span>
        </div>
        <div className="flex items-center gap-2.5">
          {chg != null && (
            <span
              className={`font-mono text-[11px] font-semibold ${
                chg >= 0 ? "text-bullish" : "text-bearish"
              }`}
            >
              {chg >= 0 ? "+" : ""}
              {chg.toFixed(2)}%
            </span>
          )}
          <div className="flex items-center gap-1.5">
            <span className="w-[5px] h-[5px] rounded-full bg-bullish" />
            <span className="font-mono text-[10px] text-terminal-dim">
              LIVE
            </span>
          </div>
        </div>
      </div>

      <div className="p-5">
        {/* Spot price */}
        <div className="mb-5">
          <p className="font-mono text-[9px] text-terminal-muted tracking-[0.12em] mb-1">
            SPOT
          </p>
          <p className="font-mono text-[32px] font-bold text-white tracking-tight leading-none">
            {signals?.spot?.toFixed(4) ?? "—"}
          </p>
        </div>

        {/* Regime label */}
        <div className="mb-5 pb-4 border-b border-[#1a1a1a]">
          <p className="font-mono text-[9px] text-terminal-muted tracking-[0.12em] mb-1.5">
            REGIME
          </p>
          <p className="font-mono text-[13px] font-bold text-white tracking-wide leading-snug">
            {call?.regime ?? "—"}
          </p>
        </div>

        {/* Confidence */}
        <div className="mb-5">
          <div className="flex justify-between items-baseline mb-1.5">
            <p className="font-mono text-[9px] text-[#444] tracking-[0.12em]">
              CONFIDENCE
            </p>
            <p
              className="font-mono text-[28px] font-bold leading-none tracking-tight"
              style={{ color: pairColor }}
            >
              {pct ?? "—"}
              <span className="text-sm font-normal text-[#555]">
                {pct != null ? "%" : ""}
              </span>
            </p>
          </div>
          <ConfidenceBar
            value={call?.confidence}
            tone="dark"
            color={pairColor}
          />
        </div>

        {/* Signal rows */}
        <div className="border-t border-terminal-border-subtle">
          {[
            ["RATE DIFF 2Y", fmt2(signals?.rate_diff_2y)],
            ["COT PERCENTILE", fmtInt(signals?.cot_percentile)],
            ["REALIZED VOL 20D", fmt2(signals?.realized_vol_20d)],
            ["IMPLIED VOL 30D", fmt2(signals?.implied_vol_30d)],
            ["SIGNAL COMPOSITE", fmt2(call?.signal_composite)],
          ].map(([label, value]) => (
            <div
              key={label}
              className="flex justify-between items-center py-2 border-b border-[#111]"
            >
              <span className="font-mono text-[10px] text-[#aaa] tracking-wider">
                {label}
              </span>
              <span className="font-mono text-xs text-white font-bold">
                {value}
              </span>
            </div>
          ))}
        </div>

        {call?.primary_driver && (
          <p className="font-mono text-[10px] text-terminal-muted mt-3.5 leading-relaxed pt-3 border-t border-terminal-border-subtle">
            {call.primary_driver}
          </p>
        )}
      </div>
    </div>
  );
}
