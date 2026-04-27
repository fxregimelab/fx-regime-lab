'use client';

import { useRouter } from 'next/navigation';
import { PAIRS, REGIME_HEATMAP_COLORS } from '@/lib/mockData';
import { useRegimeHeatmap, pivotRegimeHeatmapRows, TRACKED_PAIRS } from '@/lib/queries';

export function RegimeHeatmap() {
  const router = useRouter();
  const { data, isLoading, isError } = useRegimeHeatmap();
  const { dates, regimes } = pivotRegimeHeatmapRows(data ?? [], TRACKED_PAIRS);

  if (isLoading) {
    return (
      <div className="border border-[#e5e5e5] p-8 animate-pulse bg-[#fafafa]">
        <div className="font-mono text-[10px] text-[#aaa] tracking-widest">LOADING HEATMAP…</div>
      </div>
    );
  }

  if (isError || !dates.length) {
    return (
      <div className="border border-[#e5e5e5] p-8 bg-[#fff5f5]">
        <div className="font-mono text-[10px] text-[#dc2626] tracking-widest">HEATMAP UNAVAILABLE</div>
      </div>
    );
  }

  return (
    <div className="border border-[#e5e5e5]">
      <div className="px-5 py-3.5 border-b border-[#e5e5e5] bg-[#fafafa] flex justify-between items-center">
        <span className="font-mono text-[10px] text-[#888] tracking-widest">REGIME HEATMAP — 30 DAYS</span>
        <span className="font-mono text-[10px] text-[#bbb]">each cell = 1 trading day</span>
      </div>
      {PAIRS.map((p, pi) => (
        <div key={p.label} className="grid grid-cols-[80px_1fr]" style={{ borderBottom: pi < PAIRS.length - 1 ? '1px solid #f0f0f0' : 'none' }}>
          <div className="px-4 py-3 border-r border-[#f0f0f0] flex items-center">
            <button
              type="button"
              onClick={() => router.push(`/terminal/fx-regime/${p.urlSlug}`)}
              className="font-mono text-[11px] font-bold bg-transparent border-none cursor-pointer p-0 hover:opacity-80 transition-opacity"
              style={{ color: p.pairColor }}
            >
              {p.display}
            </button>
          </div>
          <div className="px-4 py-3 flex gap-0.5 items-center overflow-x-auto hide-scrollbar">
            {dates.map((date, i) => {
              const rowRegimes = regimes[p.label];
              const regime = rowRegimes?.[i] ?? 'UNKNOWN';
              const color = REGIME_HEATMAP_COLORS[regime] ?? '#1a1a1a';
              return (
                <div
                  key={date}
                  title={`${date}\n${regime}`}
                  className="w-3.5 h-7 shrink-0 cursor-default"
                  style={{ background: color }}
                />
              );
            })}
          </div>
        </div>
      ))}
      <div className="px-5 py-2.5 bg-[#fafafa] border-t border-[#f0f0f0] flex gap-4 flex-wrap">
        {[
          ['STRONG USD STR', '#1e3a5f'],
          ['MOD USD STR', '#2d5a8e'],
          ['NEUTRAL', '#3a3a3a'],
          ['MOD USD WEAK', '#7a3f1f'],
          ['VOL EXPANDING', '#7a5c00'],
          ['DEPRECIATION', '#8b2a2a'],
          ['APPRECIATION', '#1a5a2a'],
        ].map(([label, color]) => (
          <div key={label} className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 inline-block shrink-0" style={{ background: color }} />
            <span className="font-mono text-[9px] text-[#888]">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
