import type { BriefTabPayload } from '@/app/(site)/brief/brief-types';
import { ConfidenceBar } from '@/components/ConfidenceBar';
import { EmptyState } from '@/components/states';
import { pairTextClass, pairTopShellClass, shellDeskLinkClass } from '@/lib/pair-styles';
import type { PairMeta, SignalRow } from '@/lib/types';
import { fmt2, fmtInt, fmtSpot } from '@/lib/utils/format';
import Link from 'next/link';

export function BriefPairBlock({
  pair,
  section,
  signal,
}: {
  pair: PairMeta;
  section: BriefTabPayload | null;
  signal: SignalRow | null;
}) {
  if (!signal) {
    return (
      <p className="font-sans text-[14px] text-[#737373]">No signal baseline for {pair.display}.</p>
    );
  }

  if (!section) {
    return (
      <div className={`mb-4 border border-[#e5e5e5] bg-white ${pairTopShellClass(pair.label)}`}>
        <div className="p-6">
          <EmptyState
            title={`No brief for ${pair.display}`}
            subtitle="The pipeline has not published a brief row for this pair yet."
          />
        </div>
      </div>
    );
  }

  const pct = Math.round(section.confidence * 100);
  const paragraphs = section.analysis.split('\n\n');

  return (
    <div className={`mb-4 border border-[#e5e5e5] bg-white ${pairTopShellClass(pair.label)}`}>
      <div className="grid grid-cols-1 gap-6 border-b border-[#f0f0f0] bg-[#fafafa] px-5 py-5 sm:grid-cols-[1fr_auto] sm:items-start">
        <div>
          <div className="mb-2 flex flex-wrap items-center gap-3">
            <span className={`font-mono text-[14px] font-bold ${pairTextClass(pair.label)}`}>
              {pair.display}
            </span>
            <span className="bg-[#f0f0f0] px-2 py-0.5 font-mono text-[11px] font-bold tracking-wide text-[#0a0a0a]">
              {section.regime}
            </span>
          </div>
          {section.primaryDriver ? (
            <p className="font-sans text-[13px] leading-relaxed text-[#737373]">{section.primaryDriver}</p>
          ) : null}
        </div>
        <div className="text-left sm:text-right">
          <p className={`font-mono text-[24px] font-bold leading-none tracking-[-0.03em] ${pairTextClass(pair.label)}`}>
            {pct}
            <span className="text-[12px] font-normal text-[#aaa]">%</span>
          </p>
          <p className="mt-1 font-mono text-[9px] tracking-[0.1em] text-[#aaa]">CONFIDENCE</p>
          <div className="mx-auto mt-2 w-full max-w-[200px] sm:ml-auto sm:mr-0">
            <ConfidenceBar value={section.confidence} pairColor={pair.pairColor} barHeightPx={3} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 divide-x divide-y divide-[#f0f0f0] border-b border-[#f0f0f0] sm:grid-cols-5">
        {(
          [
            ['SPOT', fmtSpot(signal.spot, pair.label)],
            ['RATE DIFF 2Y', fmt2(signal.rate_diff_2y)],
            ['COT PCTILE', fmtInt(signal.cot_percentile)],
            ['RVOL 20D', fmt2(signal.realized_vol_20d)],
            ['COMPOSITE', fmt2(section.composite)],
          ] as const
        ).map(([label, value]) => (
          <div key={label} className="px-4 py-3.5">
            <p className="mb-1.5 font-mono text-[9px] tracking-[0.1em] text-[#aaa]">{label}</p>
            <p className="font-mono text-[14px] font-bold text-[#0a0a0a]">{value}</p>
          </div>
        ))}
      </div>

      <div className="px-5 py-6">
        {paragraphs.map((para, i) => (
          <p
            key={`${pair.label}-${i}-${para.length}`}
            className={`mb-3 font-sans text-[15px] leading-[1.75] last:mb-0 ${i === 1 ? 'font-medium text-[#111]' : 'text-[#444]'}`}
          >
            {para}
          </p>
        ))}
        <Link
          href={`/terminal/fx-regime/${pair.urlSlug}`}
          className={`mt-4 inline-block border bg-transparent px-3.5 py-2 font-mono text-[11px] transition hover:bg-[#fafafa] ${shellDeskLinkClass(pair.label)}`}
        >
          Open {pair.display} desk →
        </Link>
      </div>
    </div>
  );
}
