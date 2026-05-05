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
      {/* Ticker header */}
      <div className="mb-8">
        <p className="font-mono text-[9px] tracking-[0.2em] text-terminal-dim uppercase mb-3">
          Live Cross-Pair Overview
        </p>
        <div
          className="grid gap-px bg-terminal-border"
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
                className="block bg-terminal-surface p-5 text-left transition-colors hover:bg-[#111]"
              >
                <div className="flex justify-between items-center mb-3">
                  <span
                    className="font-mono text-[10px] font-bold tracking-wider"
                    style={{ color: p.pairColor }}
                  >
                    {p.display}
                  </span>
                  {chg != null && (
                    <span
                      className={`font-mono text-[10px] font-medium ${
                        chg >= 0 ? "text-[#7a9e7a]" : "text-[#b87a7a]"
                      }`}
                    >
                      {chg >= 0 ? "+" : ""}
                      {chg.toFixed(2)}%
                    </span>
                  )}
                </div>
                <p className="font-mono text-[28px] font-medium text-white tracking-tight leading-none mb-2 tabular-nums">
                  {sig?.spot?.toFixed(p.label === "USDJPY" ? 2 : 4) ?? "—"}
                </p>
                <p className="font-mono text-[10px] font-medium text-[#a0a0a0] tracking-wider mb-3">
                  {call?.regime ?? "—"}
                </p>
                <ConfidenceBar
                  value={call?.confidence}
                  tone="dark"
                  color={p.pairColor}
                />
                <p className="font-mono text-[9px] text-terminal-dim mt-1.5 tracking-wider">
                  CONF {fmtPct(call?.confidence)}
                </p>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Active strategy */}
      <div className="mb-6">
        <p className="font-mono text-[9px] tracking-[0.2em] text-terminal-dim uppercase mb-3">
          Strategies
        </p>
        <Link
          href="/terminal/fx-regime"
          className="block border border-terminal-border transition-colors hover:border-[#2a2a2a]"
        >
          <div className="px-5 py-3.5 border-b border-terminal-border-subtle flex justify-between items-center bg-terminal-surface">
            <div className="flex items-center gap-3">
              <span className="font-mono text-[9px] text-terminal-muted tracking-[0.12em]">
                ACTIVE
              </span>
              <span className="font-mono text-[11px] text-terminal-text font-bold">
                FX-REGIME
              </span>
            </div>
            <span className="font-mono text-[10px] text-terminal-dim">Open →</span>
          </div>
          <div
            className="grid gap-px bg-terminal-border-subtle"
            style={{ gridTemplateColumns: `repeat(${PAIRS.length}, 1fr)` }}
          >
            {PAIRS.map((p, i) => {
              const call = calls[p.label] as LatestRegimeCall | undefined;
              return (
                <div
                  key={p.label}
                  className="px-5 py-4 bg-terminal-surface"
                >
                  <p className="font-mono text-[10px] font-bold mb-1.5" style={{ color: p.pairColor }}>
                    {p.display}
                  </p>
                  <p className="font-mono text-[10px] text-[#c0c0c0] font-medium tracking-wider mb-2">
                    {call?.regime ?? "—"}
                  </p>
                  <div className="flex gap-4">
                    <span className="font-mono text-[10px] text-terminal-muted">
                      CONF{" "}
                      <span className="text-terminal-text font-medium">
                        {fmtPct(call?.confidence)}
                      </span>
                    </span>
                    <span className="font-mono text-[10px] text-terminal-dim">
                      COMP{" "}
                      <span className="text-terminal-text font-medium">
                        {fmt2(call?.signal_composite)}
                      </span>
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="px-5 py-3 flex items-center gap-1.5 bg-terminal-surface">
            <span className="w-[5px] h-[5px] rounded-full bg-[#7a9e7a] animate-gentle-pulse" />
            <span className="font-mono text-[10px] text-terminal-dim">
              Pipeline: {new Date().toISOString().slice(0, 10)}
            </span>
          </div>
        </Link>
      </div>

      <div className="border border-dashed border-terminal-border-subtle px-5 py-3.5">
        <span className="font-mono text-[9px] text-[#222] tracking-[0.1em]">
          MORE STRATEGIES — PHASE 2+
        </span>
      </div>
    </div>
  );
}
