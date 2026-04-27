import { Sparkline } from '@/components/Sparkline';
import { PAIRS } from '@/lib/mock/data';
import { pairTextClass } from '@/lib/pair-styles';

export function PerformanceSparkStrip({ series }: { series: Record<string, number[]> }) {
  return (
    <div className="grid grid-cols-1 divide-y divide-[#f0f0f0] border-t border-[#f0f0f0] sm:grid-cols-3 sm:divide-x sm:divide-y-0">
      {PAIRS.map((p) => {
        const vals = series[p.label] ?? [];
        const last = vals.length ? (vals[vals.length - 1] ?? 0) : 0;
        const lastPct = `${last >= 0 ? '+' : ''}${(last * 100).toFixed(2)}%`;
        return (
          <div key={p.label} className="px-5 py-4">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className={`font-mono text-[11px] font-bold ${pairTextClass(p.label)}`}>{p.display}</span>
              <span
                className={`font-mono text-[11px] font-bold ${last >= 0 ? 'text-[#16a34a]' : 'text-[#dc2626]'}`}
              >
                {lastPct}
              </span>
            </div>
            <Sparkline values={vals} color={p.pairColor} height={40} width={280} />
          </div>
        );
      })}
    </div>
  );
}
