"use client";

import Link from "next/link";
import { PAIRS, REGIME_HEATMAP_COLORS } from "@/lib/constants";

interface RegimeHeatmapProps {
  heatmap?: {
    dates: string[];
    regimes: Record<string, string[]>;
  } | null;
}

export function RegimeHeatmap({ heatmap }: RegimeHeatmapProps) {
  const dates = heatmap?.dates ?? [];
  const regimes = heatmap?.regimes ?? {};

  return (
    <div className="border border-shell-border">
      <div className="px-5 py-3.5 border-b border-shell-border bg-[#fafafa] flex justify-between items-center">
        <span className="font-mono text-[10px] text-[#888] tracking-[0.1em]">
          REGIME HEATMAP — 30 DAYS
        </span>
        <span className="font-mono text-[10px] text-[#bbb]">
          each cell = 1 trading day
        </span>
      </div>
      {PAIRS.map((p, pi) => (
        <div
          key={p.label}
          className="grid grid-cols-[80px_1fr]"
          style={{
            borderBottom: pi < PAIRS.length - 1 ? "1px solid #f0f0f0" : "none",
          }}
        >
          <div className="px-4 py-3 border-r border-[#f0f0f0] flex items-center">
            <Link
              href={`/terminal/fx-regime/${p.urlSlug}`}
              className="font-mono text-[11px] font-bold cursor-pointer"
              style={{ color: p.pairColor }}
            >
              {p.display}
            </Link>
          </div>
          <div className="px-4 py-3 flex gap-0.5 items-center overflow-x-auto">
            {dates.map((date, i) => {
              const regime = regimes[p.label]?.[i] ?? "UNKNOWN";
              const color = REGIME_HEATMAP_COLORS[regime] ?? "#1a1a1a";
              return (
                <div
                  key={date}
                  title={`${date}: ${regime}`}
                  className="w-3.5 h-7 flex-shrink-0 cursor-default"
                  style={{ background: color }}
                />
              );
            })}
          </div>
        </div>
      ))}
      <div className="px-5 py-2.5 bg-[#fafafa] border-t border-[#f0f0f0] flex gap-4 flex-wrap">
        {[
          ["STRONG USD STR", "#1e3a5f"],
          ["MOD USD STR", "#2d5a8e"],
          ["NEUTRAL", "#3a3a3a"],
          ["MOD USD WEAK", "#7a3f1f"],
          ["VOL EXPANDING", "#7a5c00"],
          ["DEPRECIATION", "#8b2a2a"],
          ["APPRECIATION", "#1a5a2a"],
        ].map(([label, color]) => (
          <div key={label} className="flex items-center gap-1">
            <span
              className="w-2.5 h-2.5 inline-block flex-shrink-0"
              style={{ background: color }}
            />
            <span className="font-mono text-[9px] text-[#888]">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
