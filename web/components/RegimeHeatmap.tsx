import { PAIR_LABELS, regimeHeatmapCellClass } from '@/lib/pair-styles';
import type { HeatmapData, PairMeta } from '@/lib/types';

const shellWrap = 'border border-[#e5e5e5] bg-white';
const termWrap = 'border border-[#1e1e1e] bg-[#0c0c0c]';

export function RegimeHeatmap({
  data,
  colors,
  pairLabels = PAIR_LABELS,
  variant = 'default',
}: {
  data: HeatmapData;
  colors: Record<string, string>;
  pairLabels?: PairMeta['label'][];
  variant?: 'default' | 'terminal';
}) {
  const isTerminal = variant === 'terminal';
  const wrap = isTerminal ? termWrap : shellWrap;
  const headerBg = isTerminal ? 'bg-[#0d0d0d] border-[#1e1e1e]' : 'bg-[#fafafa] border-[#e5e5e5]';
  const headerText = isTerminal ? 'text-[#555]' : 'text-[#888]';
  const rowBorder = isTerminal ? 'border-[#1e1e1e]' : 'border-[#f0f0f0]';
  const labelBorder = isTerminal ? 'border-[#1e1e1e]' : 'border-[#e5e5e5]';
  const labelText = isTerminal ? 'text-[#e8e8e8]' : 'text-[#0a0a0a]';
  const legendText = isTerminal ? 'text-[#555]' : 'text-[#888]';
  const legendBg = isTerminal ? 'bg-[#0d0d0d] border-[#1e1e1e]' : 'bg-[#fafafa] border-[#e5e5e5]';

  return (
    <div className={wrap}>
      <div className={`flex items-center justify-between border-b px-5 py-3 ${headerBg}`}>
        <span className={`font-mono text-[10px] tracking-[0.1em] ${headerText}`}>
          REGIME HEATMAP — 30 DAYS
        </span>
        <span className={`font-mono text-[10px] opacity-60 ${headerText}`}>
          each cell = 1 trading day
        </span>
      </div>

      {pairLabels.map((label, pi) => {
        const series = data.regimes[label] ?? [];
        const isLast = pi === pairLabels.length - 1;
        return (
          <div
            key={label}
            className={`grid grid-cols-[80px_minmax(0,1fr)] border-b ${rowBorder} ${isLast ? 'border-b-0' : ''}`}
          >
            <div className={`flex items-center border-r px-4 py-3 ${labelBorder}`}>
              <span className={`font-mono text-[11px] font-bold ${labelText}`}>{label}</span>
            </div>
            <div className="overflow-x-auto px-4 py-3">
              <div className="flex items-center gap-[2px]">
                {series.slice(0, 30).map((regime, i) => {
                  const dateKey = data.dates[i] ?? `d${i}`;
                  return (
                    <div
                      key={`${label}-${dateKey}`}
                      title={`${dateKey}\n${regime}`}
                      className={`h-[28px] w-[14px] shrink-0 ${regimeHeatmapCellClass(regime, colors)}`}
                    />
                  );
                })}
              </div>
            </div>
          </div>
        );
      })}

      <div className={`flex flex-wrap gap-x-4 gap-y-2 border-t px-5 py-3 ${legendBg}`}>
        {Object.entries(colors)
          .filter(([key]) => key !== 'UNKNOWN')
          .map(([regime, hex]) => (
            <div key={regime} className="flex items-center gap-1.5">
              <span
                className={`inline-block h-[10px] w-[10px] shrink-0 ${regimeHeatmapCellClass(regime, {
                  ...colors,
                  [regime]: hex,
                })}`}
              />
              <span className={`font-mono text-[9px] tracking-[0.06em] ${legendText}`}>
                {regime.replace(/_/g, ' ')}
              </span>
            </div>
          ))}
      </div>
    </div>
  );
}
