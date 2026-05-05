import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import {
  getLatestRegimeCalls,
  getLatestSignals,
} from "@/lib/supabase/queries";
import { ConfidenceBar } from "@/components/ui/confidence-bar";
import { fmt2, fmtPct } from "@/components/ui/utils";
import { PAIRS } from "@/lib/constants";
import type { LatestRegimeCall, LatestSignal } from "@/lib/supabase/queries";

export default async function TerminalIndexPage() {
  const supabase = await createClient();

  const [calls, signals] = await Promise.all([
    getLatestRegimeCalls(supabase),
    getLatestSignals(supabase),
  ]);

  return (
    <div>
      {/* Cross-pair overview ticker */}
      <div
        className="grid gap-0.5 mb-8"
        style={{ gridTemplateColumns: `repeat(${PAIRS.length}, 1fr)` }}
      >
        {PAIRS.map((p) => {
          const call = calls[p.label] as LatestRegimeCall | undefined;
          const sig = signals[p.label] as LatestSignal | undefined;
          const chg = sig?.day_change_pct;
          return (
            <Link
              key={p.label}
              href={`/terminal/fx-regime/${p.urlSlug}`}
              className="block bg-terminal-surface border border-terminal-border py-4 px-4 text-left transition-colors hover:bg-[#111]"
              style={{ borderTop: `2px solid ${p.pairColor}` }}
            >
              <div className="flex justify-between items-center mb-2">
                <span
                  className="font-mono text-xs font-bold tracking-wider"
                  style={{ color: p.pairColor }}
                >
                  {p.display}
                </span>
                {chg != null && (
                  <span
                    className={`font-mono text-[11px] font-bold ${
                      chg >= 0 ? "text-bullish" : "text-bearish"
                    }`}
                  >
                    {chg >= 0 ? "+" : ""}
                    {chg.toFixed(2)}%
                  </span>
                )}
              </div>
              <p className="font-mono text-[26px] font-bold text-white tracking-tight leading-none mb-1.5">
                {sig?.spot?.toFixed(p.label === "USDJPY" ? 2 : 4) ?? "—"}
              </p>
              <p className="font-mono text-[10px] font-bold text-[#c0c0c0] tracking-wider mb-2.5">
                {call?.regime ?? "—"}
              </p>
              <ConfidenceBar
                value={call?.confidence}
                tone="dark"
                color={p.pairColor}
              />
              <p className="font-mono text-[9px] text-terminal-dim mt-1 tracking-wider">
                CONF {fmtPct(call?.confidence)}
              </p>
            </Link>
          );
        })}
      </div>

      <p className="font-mono text-[9px] text-[#666] tracking-[0.12em] mb-3">
        STRATEGIES
      </p>

      <Link
        href="/terminal/fx-regime"
        className="block border border-terminal-border transition-colors hover:border-[#2a2a2a]"
      >
        <div className="px-5 py-3.5 border-b border-[#1a1a1a] flex justify-between items-center bg-[#0c0c0c]">
          <div className="flex items-center gap-3">
            <span className="font-mono text-[9px] text-[#777] tracking-[0.12em]">
              ACTIVE STRATEGY
            </span>
            <span className="font-mono text-[11px] text-brand-accent font-bold">
              FX-REGIME
            </span>
          </div>
          <span className="font-mono text-[10px] text-[#666]">Open →</span>
        </div>
        <div
          className="grid gap-0.5 border-b border-[#141414]"
          style={{
            gridTemplateColumns: `repeat(${PAIRS.length}, 1fr)`,
          }}
        >
          {PAIRS.map((p, i) => {
            const call = calls[p.label] as LatestRegimeCall | undefined;
            return (
              <div
                key={p.label}
                className="px-5 py-4"
                style={{
                  borderRight: i < PAIRS.length - 1 ? "1px solid #141414" : "none",
                }}
              >
                <p className="font-mono text-[10px] font-bold mb-1.5" style={{ color: p.pairColor }}>
                  {p.display}
                </p>
                <p className="font-mono text-[10px] text-[#c0c0c0] font-bold tracking-wider mb-2">
                  {call?.regime ?? "—"}
                </p>
                <div className="flex gap-4">
                  <span className="font-mono text-[10px] text-[#999]">
                    CONF{" "}
                    <span className="text-[#e0e0e0] font-bold">
                      {fmtPct(call?.confidence)}
                    </span>
                  </span>
                  <span className="font-mono text-[10px] text-[#666]">
                    COMPOSITE{" "}
                    <span className="text-[#e0e0e0] font-bold">
                      {fmt2(call?.signal_composite)}
                    </span>
                  </span>
                </div>
              </div>
            );
          })}
        </div>
        <div className="px-5 py-3 flex items-center gap-1.5">
          <span className="w-[5px] h-[5px] rounded-full bg-bullish" />
          <span className="font-mono text-[10px] text-[#777]">
            Pipeline: {new Date().toISOString().slice(0, 10)}
          </span>
        </div>
      </Link>

      <div className="border border-dashed border-[#141414] mt-0.5 px-5 py-3.5">
        <span className="font-mono text-[9px] text-[#222] tracking-[0.1em]">
          MORE STRATEGIES — PHASE 2+
        </span>
      </div>
    </div>
  );
}
