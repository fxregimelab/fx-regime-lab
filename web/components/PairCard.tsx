import { ConfidenceBar } from '@/components/ConfidenceBar';
import { pairTextClass, pairTopShellClass } from '@/lib/pair-styles';
import type { PairMeta, RegimeCall, SignalRow } from '@/lib/types';
import { fmt2, fmtChg, fmtInt, fmtSpot } from '@/lib/utils/format';
import Link from 'next/link';

export function PairCard({
  pair,
  regime,
  signal,
}: {
  pair: PairMeta;
  regime: RegimeCall;
  signal: SignalRow;
}) {
  const chg = fmtChg(signal.day_change_pct);
  const pct = regime ? Math.round(regime.confidence * 100) : null;

  return (
    <Link
      href={`/pairs/${pair.urlSlug}`}
      className={`group flex min-h-[200px] flex-col border border-[#e5e5e5] bg-white p-5 transition hover:border-[#bbb] hover:bg-[#fafafa] ${pairTopShellClass(pair.label)}`}
    >
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <p className="mb-1 font-sans text-[14px] font-bold text-[#0a0a0a]">{pair.display}</p>
          <p className="font-mono text-[20px] font-bold leading-none tracking-[-0.02em] text-[#0a0a0a]">
            {fmtSpot(signal.spot, pair.label)}
          </p>
        </div>
        {chg.dir !== 'flat' && (
          <span
            className={`shrink-0 px-2 py-0.5 font-mono text-[11px] font-semibold ${
              chg.dir === 'up' ? 'bg-[#f0fdf4] text-[#16a34a]' : 'bg-[#fff5f5] text-[#dc2626]'
            }`}
          >
            {chg.str}
          </span>
        )}
      </div>

      <p className="mb-3 min-h-[2.5rem] font-mono text-[11px] font-bold leading-snug tracking-[0.03em] text-[#111]">
        {regime.regime}
      </p>

      <div className="mb-4">
        <ConfidenceBar value={regime.confidence} pairColor={pair.pairColor} barHeightPx={4} />
        <div className="mt-1.5 flex items-baseline justify-between">
          <span className="font-mono text-[9px] tracking-[0.1em] text-[#888]">CONFIDENCE</span>
          <span className="font-mono text-[11px] font-bold text-[#0a0a0a]">
            {pct != null ? `${pct}%` : '-'}
          </span>
        </div>
      </div>

      <div className="flex flex-col gap-[7px] border-t border-[#f0f0f0] pt-3">
        {([
          ['Rate diff 2Y', fmt2(signal.rate_diff_2y)],
          ['COT pctile', fmtInt(signal.cot_percentile)],
          ['Rvol 20d', fmt2(signal.realized_vol_20d)],
        ] as [string, string][]).map(([lbl, val]) => (
          <div key={lbl} className="flex items-baseline justify-between">
            <span className="font-mono text-[10px] text-[#888]">{lbl}</span>
            <span className="font-mono text-[11px] font-semibold text-[#111]">{val}</span>
          </div>
        ))}
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-[#f0f0f0] pt-3">
        <span className="font-mono text-[9px] tracking-[0.08em] text-[#aaa]">OPEN DESK</span>
        <span className={`font-mono text-[11px] font-bold ${pairTextClass(pair.label)}`}>→</span>
      </div>
    </Link>
  );
}
