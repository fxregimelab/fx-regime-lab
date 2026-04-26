import { ConfidenceBar } from '@/components/ConfidenceBar';
import { pairBgClass, pairTextClass } from '@/lib/pair-styles';
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
  return (
    <Link
      href={`/pairs/${pair.urlSlug}`}
      className="group flex border border-[#e5e5e5] bg-white transition hover:shadow-sm"
    >
      <span className={`w-0.5 shrink-0 ${pairBgClass(pair.label)}`} aria-hidden />
      <div className="min-w-0 flex-1 p-4">
        <div className="mb-3 flex items-start justify-between gap-2">
          <span className={`font-mono text-[10px] ${pairTextClass(pair.label)}`}>
            {pair.display}
          </span>
          <span className="font-mono text-[14px] text-[#0a0a0a]">
            {fmtSpot(signal.spot, pair.label)}
          </span>
        </div>
        <p className="mb-1 font-sans text-[13px] font-semibold uppercase text-[#0a0a0a]">
          {regime.regime}
        </p>
        <ConfidenceBar value={regime.confidence} pairColor={pair.pairColor} />
        <div className="mt-3 grid grid-cols-3 gap-2 border-t border-[#f0f0f0] pt-3">
          <div>
            <p className="font-mono text-[9px] text-[#a0a0a0]">RATE DIFF 2Y</p>
            <p className="font-mono text-[10px] text-[#0a0a0a]">{fmt2(signal.rate_diff_2y)}</p>
          </div>
          <div>
            <p className="font-mono text-[9px] text-[#a0a0a0]">COT %</p>
            <p className="font-mono text-[10px] text-[#0a0a0a]">{fmtInt(signal.cot_percentile)}</p>
          </div>
          <div>
            <p className="font-mono text-[9px] text-[#a0a0a0]">REAL VOL 20D</p>
            <p className="font-mono text-[10px] text-[#0a0a0a]">{fmt2(signal.realized_vol_20d)}</p>
          </div>
        </div>
        <p
          className={`mt-2 text-right font-mono text-[10px] ${chg.positive ? 'text-[#16a34a]' : 'text-[#dc2626]'}`}
        >
          {chg.str}
        </p>
      </div>
    </Link>
  );
}
