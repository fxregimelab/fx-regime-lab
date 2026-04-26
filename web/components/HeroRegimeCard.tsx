import { ConfidenceBar } from '@/components/ConfidenceBar';
import { pairBgClass, pairTextClass } from '@/lib/pair-styles';
import type { PairMeta, RegimeCall, SignalRow } from '@/lib/types';
import { fmt2, fmtChg, fmtSpot } from '@/lib/utils/format';

export function HeroRegimeCard({
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
    <div className="flex w-full border border-[#e5e5e5] bg-white">
      <span className={`w-1 shrink-0 ${pairBgClass(pair.label)}`} aria-hidden />
      <div className="flex-1 p-5">
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
          <span className={`font-mono text-[10px] ${pairTextClass(pair.label)}`}>{pair.label}</span>
          <div className="flex items-baseline gap-3">
            <span className="font-mono text-[18px] text-[#0a0a0a]">
              {fmtSpot(signal.spot, pair.label)}
            </span>
            <span
              className={`font-mono text-[11px] ${chg.positive ? 'text-[#16a34a]' : 'text-[#dc2626]'}`}
            >
              {chg.str}
            </span>
          </div>
        </div>
        <p className="mb-2 font-sans text-[16px] font-semibold uppercase leading-snug text-[#0a0a0a]">
          {regime.regime}
        </p>
        <ConfidenceBar value={regime.confidence} pairColor={pair.pairColor} />
        <div className="mt-4 flex flex-wrap items-baseline justify-between gap-2 border-t border-[#f0f0f0] pt-4">
          <span className="font-mono text-[11px] text-[#737373]">
            Composite {fmt2(regime.signal_composite)}
          </span>
          <span className="max-w-[min(100%,280px)] font-sans text-[12px] text-[#737373]">
            {regime.primary_driver}
          </span>
        </div>
      </div>
    </div>
  );
}
