import { ConfidenceBar } from '@/components/ConfidenceBar';
import { REGIME_HEATMAP_COLORS } from '@/lib/mock/data';
import { regimeHeatmapCellClass } from '@/lib/pair-styles';
import type { HistoryRow } from '@/lib/types';

export function HistoryTab({ history, pairColor }: { history: HistoryRow[]; pairColor: string }) {
  return (
    <div className="border border-[#1e1e1e]">
      <div className="grid grid-cols-[1fr_1fr_100px] border-b border-[#1e1e1e] bg-[#0c0c0c] px-2 py-2">
        <span className="font-mono text-[8px] font-normal tracking-widest text-[#555]">DATE</span>
        <span className="font-mono text-[8px] font-normal tracking-widest text-[#555]">REGIME</span>
        <span className="text-right font-mono text-[8px] font-normal tracking-widest text-[#555]">
          CONF
        </span>
      </div>
      {history.map((row, i) => (
        <div
          key={row.date}
          className={`grid grid-cols-[1fr_1fr_100px] items-center border-b border-[#1e1e1e] px-2 py-2 last:border-b-0 ${
            i % 2 === 0 ? 'bg-[#080808]' : 'bg-[#0c0c0c]'
          }`}
        >
          <span className="font-mono text-[11px] text-[#e8e8e8]">{row.date}</span>
          <div className="flex min-w-0 items-center gap-1.5">
            <span
              className={`h-1.5 w-1.5 shrink-0 ${regimeHeatmapCellClass(row.regime, REGIME_HEATMAP_COLORS)}`}
            />
            <span className="truncate font-mono text-[11px] text-[#e8e8e8]">{row.regime}</span>
          </div>
          <div className="flex justify-end">
            <div className="w-[60px]">
              <ConfidenceBar
                value={row.confidence}
                pairColor={pairColor}
                variant="dark"
                barHeightPx={3}
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
