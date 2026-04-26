import { PAIR_LABELS, regimeHeatmapCellClass } from '@/lib/pair-styles';
import type { HeatmapData, PairMeta } from '@/lib/types';

const shellRow = 'border-b border-[#e5e5e5] last:border-b-0';
const shellLabelCell = 'flex w-16 shrink-0 items-center border-r border-[#e5e5e5] px-2 py-2';
const shellLabelText = 'font-mono text-[9px] text-[#0a0a0a]';
const shellWrap = 'border border-[#e5e5e5] bg-white';

const termRow = 'border-b border-[#1e1e1e] last:border-b-0';
const termLabelCell = 'flex w-16 shrink-0 items-center border-r border-[#1e1e1e] px-2 py-2';
const termLabelText = 'font-mono text-[9px] text-[#e8e8e8]';
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
  const row = isTerminal ? termRow : shellRow;
  const labelCell = isTerminal ? termLabelCell : shellLabelCell;
  const labelText = isTerminal ? termLabelText : shellLabelText;

  return (
    <div className={wrap}>
      {pairLabels.map((label) => {
        const series = data.regimes[label] ?? [];
        return (
          <div key={label} className={`flex ${row}`}>
            <div className={labelCell}>
              <span className={labelText}>{label}</span>
            </div>
            <div className="overflow-x-auto p-2">
              <div className="grid w-max grid-cols-6 grid-rows-5 gap-px">
                {series.slice(0, 30).map((regime, i) => {
                  const dateKey = data.dates[i] ?? `d${i}`;
                  return (
                    <div
                      key={`${label}-${dateKey}`}
                      className={`h-[18px] w-[28px] shrink-0 ${regimeHeatmapCellClass(regime, colors)}`}
                    />
                  );
                })}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
