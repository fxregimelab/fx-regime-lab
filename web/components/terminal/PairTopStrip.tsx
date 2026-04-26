import { ConfidenceBar } from '@/components/ConfidenceBar';
import type { PairMeta, RegimeCall, SignalRow } from '@/lib/types';
import { fmt2, fmtSpot } from '@/lib/utils/format';

function compositeClass(v: number, pairColor: string) {
  if (Math.abs(v) < 0.1) return 'text-[#555]';
  if (v > 0) {
    if (pairColor === '#4BA3E3') return 'text-[#4BA3E3]';
    if (pairColor === '#F5923A') return 'text-[#F5923A]';
    return 'text-[#D94030]';
  }
  return 'text-[#dc2626]';
}

export function PairTopStrip({
  pair,
  regime,
  signal,
}: {
  pair: PairMeta;
  regime: RegimeCall;
  signal: SignalRow;
}) {
  const chg = signal.day_change;
  const chgPos = chg >= 0;

  return (
    <div className="grid border-b border-[#1e1e1e] bg-[#0c0c0c] px-4 py-3 sm:px-6 lg:grid-cols-4">
      <div className="border-b border-[#1e1e1e] py-2 sm:py-0 lg:border-b-0 lg:border-r lg:pr-4">
        <p className="font-mono text-[9px] text-[#555]">{pair.display}</p>
        <p className="mt-0.5 font-mono text-[20px] text-[#e8e8e8]">
          {fmtSpot(signal.spot, pair.label)}
        </p>
        <p
          className={`mt-0.5 font-mono text-[11px] ${chgPos ? 'text-[#16a34a]' : 'text-[#dc2626]'}`}
        >
          {chgPos ? '+' : ''}
          {fmt2(chg)} day
        </p>
      </div>
      <div className="border-b border-[#1e1e1e] py-2 sm:py-0 lg:border-b-0 lg:border-r lg:px-4">
        <p className="font-sans text-[13px] font-semibold uppercase leading-tight text-[#e8e8e8]">
          {regime.regime}
        </p>
        <div className="mt-1.5 max-w-xs">
          <ConfidenceBar value={regime.confidence} pairColor={pair.pairColor} variant="dark" />
        </div>
      </div>
      <div className="border-b border-[#1e1e1e] py-2 sm:py-0 lg:border-b-0 lg:border-r lg:px-4">
        <p className="font-mono text-[9px] text-[#555]">COMPOSITE</p>
        <p
          className={`mt-0.5 font-mono text-[20px] ${compositeClass(regime.signal_composite, pair.pairColor)}`}
        >
          {fmt2(regime.signal_composite)}
        </p>
      </div>
      <div className="py-2 sm:py-0 lg:pl-4">
        <p className="font-mono text-[9px] text-[#555]">SIGNAL</p>
        <p className="mt-0.5 font-sans text-[13px] font-semibold text-[#e8e8e8]">
          {regime.rate_signal}
        </p>
        <p className="mt-1 font-sans text-[12px] text-[#737373]">{regime.primary_driver}</p>
      </div>
    </div>
  );
}
