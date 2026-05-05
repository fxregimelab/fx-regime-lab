"use client";

import Link from "next/link";
import { useState } from "react";
import { ConfidenceBar } from "@/components/ui/confidence-bar";
import { fmt2, fmtInt } from "@/components/ui/utils";
import type { LatestRegimeCall, LatestSignal } from "@/lib/supabase/queries";
import type { PairMeta } from "@/lib/constants";

interface PairCardProps {
  pair: PairMeta;
  call?: LatestRegimeCall | null;
  signals?: LatestSignal | null;
}

export function PairCard({ pair, call, signals }: PairCardProps) {
  const [hov, setHov] = useState(false);
  const pct = call ? Math.round(call.confidence * 100) : null;
  const chg = signals?.day_change_pct;

  return (
    <Link
      href={`/terminal/fx-regime/${pair.urlSlug}`}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      className="block cursor-pointer transition-all duration-150 p-5"
      style={{
        border: `1px solid ${hov ? "#bbb" : "#e5e5e5"}`,
        background: hov ? "#fafafa" : "#fff",
        borderTop: `3px solid ${pair.pairColor}`,
      }}
    >
      <div className="flex justify-between items-start mb-3">
        <div>
          <p className="font-sans font-bold text-[15px] text-shell-text mb-0.5">
            {pair.display}
          </p>
          <p className="font-mono text-xl font-bold text-shell-text tracking-tight">
            {signals?.spot?.toFixed(pair.label === "USDJPY" ? 2 : 4) ?? "—"}
          </p>
        </div>
        {chg != null && (
          <span
            className={`font-mono text-xs font-semibold px-2 py-0.5 ${
              chg >= 0
                ? "text-up-shell bg-[#f0fdf4]"
                : "text-down-shell bg-[#fff5f5]"
            }`}
          >
            {chg >= 0 ? "+" : ""}
            {chg.toFixed(2)}%
          </span>
        )}
      </div>

      <p className="font-mono text-[11px] font-bold text-[#111] tracking-wide leading-snug mb-3">
        {call?.regime ?? "—"}
      </p>

      <div className="mb-3.5">
        <ConfidenceBar
          value={call?.confidence}
          tone="light"
          color={pair.pairColor}
        />
        <div className="flex justify-between mt-1.5">
          <span className="font-mono text-[9px] text-shell-muted tracking-[0.1em]">
            CONFIDENCE
          </span>
          <span className="font-mono text-[11px] text-shell-text font-bold">
            {pct != null ? `${pct}%` : "—"}
          </span>
        </div>
      </div>

      <div className="border-t border-[#f0f0f0] pt-3 flex flex-col gap-1.5">
        {[
          ["Rate diff 2Y", fmt2(signals?.rate_diff_2y)],
          ["COT pctile", fmtInt(signals?.cot_percentile)],
          ["Rvol 20d", fmt2(signals?.realized_vol_20d)],
        ].map(([lbl, val]) => (
          <div key={lbl} className="flex justify-between">
            <span className="font-mono text-[10px] text-shell-muted">
              {lbl}
            </span>
            <span className="font-mono text-[11px] text-[#111] font-semibold">
              {val}
            </span>
          </div>
        ))}
      </div>

      <div className="mt-3.5 pt-2.5 border-t border-[#f0f0f0] flex justify-between items-center">
        <span className="font-mono text-[9px] text-[#aaa] tracking-[0.08em]">
          OPEN DESK
        </span>
        <span
          className="font-mono text-[11px] font-bold"
          style={{ color: pair.pairColor }}
        >
          →
        </span>
      </div>
    </Link>
  );
}
