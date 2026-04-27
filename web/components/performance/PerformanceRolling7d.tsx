import { PAIRS } from '@/lib/mock/data';
import { pairFillHex, pairTextClass } from '@/lib/pair-styles';
import type { PairMeta } from '@/lib/types';

export function PerformanceRolling7d({
  perPairRolling,
}: {
  perPairRolling: Record<string, { pct: number | null; n: number }>;
}) {
  return (
    <div className="mb-10 border border-[#e5e5e5]">
      <div className="border-b border-[#f0f0f0] px-5 py-4">
        <p className="font-mono text-[10px] tracking-[0.1em] text-[#888]">ROLLING 7-DAY ACCURACY</p>
      </div>
      <div className="grid grid-cols-1 divide-y divide-[#f0f0f0] sm:grid-cols-3 sm:divide-x sm:divide-y-0">
        {PAIRS.map((p: PairMeta) => {
          const { pct, n } = perPairRolling[p.label] ?? { pct: null, n: 0 };
          const accStr = pct != null ? `${pct >= 10 ? pct.toFixed(0) : pct.toFixed(1)}%` : '—';
          const w = pct != null ? Math.min(100, Math.max(0, pct)) : 0;
          const fill = pairFillHex(p.label);
          return (
            <div key={p.label} className="px-5 py-4">
              <p className={`mb-1 font-mono text-[10px] font-bold ${pairTextClass(p.label)}`}>{p.display}</p>
              <p className="font-mono text-[26px] font-bold leading-none tracking-[-0.03em] text-[#0a0a0a]">
                {accStr}
              </p>
              <p className="mt-1 font-mono text-[10px] text-[#bbb]">{n} calls</p>
              <svg viewBox="0 0 100 3" className="mt-2.5 h-[3px] w-full" preserveAspectRatio="none" role="img">
                <title>Accuracy bar</title>
                <rect width="100" height="3" fill="#f0f0f0" />
                <rect width={w} height="3" fill={fill} />
              </svg>
            </div>
          );
        })}
      </div>
    </div>
  );
}
