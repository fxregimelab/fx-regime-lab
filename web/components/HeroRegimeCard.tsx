import { ConfidenceBar } from '@/components/ConfidenceBar';
import { pairBgClass, pairTextClass } from '@/lib/pair-styles';
import type { PairMeta, RegimeCall, SignalRow } from '@/lib/types';
import { fmt2, fmtChg, fmtInt, fmtSpot } from '@/lib/utils/format';

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
  const pct = Math.round(regime.confidence * 100);

  return (
    <div className="border border-[#1e1e1e] bg-[#080808]">
      <div className="flex items-center justify-between border-b border-[#1a1a1a] px-5 py-3.5">
        <div className="flex items-center gap-2">
          <span className={`inline-block h-2 w-2 shrink-0 rounded-full ${pairBgClass(pair.label)}`} />
          <span className={`font-mono text-[12px] font-bold tracking-[0.04em] ${pairTextClass(pair.label)}`}>
            {pair.display}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {chg.dir !== 'flat' && (
            <span
              className={`font-mono text-[11px] font-semibold ${chg.dir === 'up' ? 'text-[#4ade80]' : 'text-[#f87171]'}`}
            >
              {chg.str}
            </span>
          )}
          <div className="flex items-center gap-1.5">
            <span className="inline-block h-[5px] w-[5px] shrink-0 rounded-full bg-[#4ade80]" />
            <span className="font-mono text-[10px] text-[#555]">LIVE</span>
          </div>
        </div>
      </div>

      <div className="p-5">
        <div className="mb-5">
          <p className="mb-1 font-mono text-[9px] tracking-[0.12em] text-[#999]">SPOT</p>
          <p className="font-mono text-[32px] font-bold leading-none tracking-[-0.02em] text-white">
            {fmtSpot(signal.spot, pair.label)}
          </p>
        </div>

        <div className="mb-5 border-b border-[#1a1a1a] pb-4">
          <p className="mb-1.5 font-mono text-[9px] tracking-[0.12em] text-[#999]">REGIME</p>
          <p className="font-mono text-[13px] font-bold leading-snug tracking-[0.04em] text-white">
            {regime.regime}
          </p>
        </div>

        <div className="mb-5">
          <div className="mb-1.5 flex items-baseline justify-between">
            <p className="font-mono text-[9px] tracking-[0.12em] text-[#444]">CONFIDENCE</p>
            <p className={`font-mono text-[28px] font-bold leading-none tracking-[-0.03em] ${pairTextClass(pair.label)}`}>
              {pct}
              <span className="text-[14px] font-normal text-[#555]">%</span>
            </p>
          </div>
          <ConfidenceBar value={regime.confidence} pairColor={pair.pairColor} variant="dark" barHeightPx={4} />
        </div>

        <div className="border-t border-[#141414]">
          {([
            ['RATE DIFF 2Y', fmt2(signal.rate_diff_2y)],
            ['COT PERCENTILE', fmtInt(signal.cot_percentile)],
            ['REALIZED VOL 20D', fmt2(signal.realized_vol_20d)],
            ['SIGNAL COMPOSITE', fmt2(regime.signal_composite)],
          ] as [string, string][]).map(([label, value]) => (
            <div
              key={label}
              className="flex items-center justify-between border-b border-[#111] py-2.5"
            >
              <span className="font-mono text-[10px] tracking-[0.06em] text-[#aaa]">{label}</span>
              <span className="font-mono text-[12px] font-bold text-white">{value}</span>
            </div>
          ))}
        </div>

        {regime.primary_driver && (
          <p className="mt-3.5 border-t border-[#141414] pt-3 font-mono text-[10px] leading-[1.7] text-[#999]">
            {regime.primary_driver}
          </p>
        )}
      </div>
    </div>
  );
}
