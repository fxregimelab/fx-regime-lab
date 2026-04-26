'use client';

import { ConfidenceBar } from '@/components/ConfidenceBar';
import { ValidationTable } from '@/components/ValidationTable';
import { EmptyState } from '@/components/states';
import { PAIRS } from '@/lib/mock/data';
import { pairTextClass } from '@/lib/pair-styles';
import type { PairMeta, SignalRow, ValidationRow } from '@/lib/types';
import { fmt2, fmtInt } from '@/lib/utils/format';
import { useState } from 'react';

export type BriefTabPayload = {
  regime: string;
  confidence: number;
  composite: number;
  analysis: string;
  primaryDriver: string | null;
};

export function BriefTabs({
  briefByLabel,
  signalByLabel,
  validationRows,
}: {
  briefByLabel: Record<PairMeta['label'], BriefTabPayload | null>;
  signalByLabel: Record<PairMeta['label'], SignalRow | null>;
  validationRows: ValidationRow[];
}) {
  const [active, setActive] = useState<PairMeta['label']>('EURUSD');
  const pair = PAIRS.find((p) => p.label === active) ?? PAIRS[0];
  const signal = signalByLabel[active];
  const section = briefByLabel[active];
  const rows = validationRows.filter((r) => r.pair === pair.label);

  if (!signal) {
    return (
      <p className="font-sans text-[14px] text-[#737373]">No signal baseline for this pair.</p>
    );
  }

  if (!section) {
    return (
      <div>
        <div className="mb-8 flex gap-0 overflow-x-auto border-b border-[#e5e5e5]">
          {PAIRS.map((p) => (
            <button
              key={p.label}
              type="button"
              onClick={() => setActive(p.label)}
              className={`border-b-2 px-4 py-3 font-mono text-[11px] font-semibold ${
                active === p.label
                  ? 'border-[#F5923A] text-[#0a0a0a]'
                  : 'border-transparent text-[#a0a0a0]'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
        <EmptyState
          title={`No brief for ${active}`}
          subtitle="The pipeline has not published a brief row for this pair yet."
        />
      </div>
    );
  }

  const paragraphs = section.analysis.split('\n\n');

  return (
    <div>
      <div className="mb-8 flex gap-0 overflow-x-auto border-b border-[#e5e5e5]">
        {PAIRS.map((p) => (
          <button
            key={p.label}
            type="button"
            onClick={() => setActive(p.label)}
            className={`border-b-2 px-4 py-3 font-mono text-[11px] font-semibold ${
              active === p.label
                ? 'border-[#F5923A] text-[#0a0a0a]'
                : 'border-transparent text-[#a0a0a0]'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="mb-6">
        <p className="font-sans text-[20px] font-semibold uppercase text-[#0a0a0a]">
          {section.regime}
        </p>
        <p className="mt-1 font-mono text-[11px] text-[#737373]">
          Confidence {Math.round(section.confidence * 100)}%
        </p>
        <div className="mt-2 max-w-md">
          <ConfidenceBar value={section.confidence} pairColor={pair.pairColor} />
        </div>
        {section.primaryDriver ? (
          <p className="mt-3 font-mono text-[11px] leading-relaxed text-[#525252]">
            <span className="text-[#a0a0a0]">PRIMARY DRIVER </span>
            {section.primaryDriver}
          </p>
        ) : null}
      </div>

      <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-5">
        {[
          { k: 'RATE DIFF 2Y', v: fmt2(signal.rate_diff_2y) },
          { k: 'COT %', v: fmtInt(signal.cot_percentile) },
          { k: 'REAL VOL 20D', v: fmt2(signal.realized_vol_20d) },
          { k: 'REAL VOL 5D', v: fmt2(signal.realized_vol_5d) },
          { k: 'COMPOSITE', v: fmt2(section.composite) },
        ].map((col) => (
          <div key={col.k} className="border border-[#e5e5e5] p-3">
            <p className="font-mono text-[9px] tracking-wide text-[#a0a0a0]">{col.k}</p>
            <p className="mt-1 font-mono text-[16px] font-bold text-[#0a0a0a]">{col.v}</p>
          </div>
        ))}
      </div>

      <div className="mb-10 space-y-4">
        {paragraphs.map((para) => (
          <p
            key={`${active}-${para.length}-${para.charCodeAt(0)}`}
            className="font-sans text-[14px] leading-relaxed text-[#444]"
          >
            {para}
          </p>
        ))}
      </div>

      <div>
        <p className={`mb-3 font-mono text-[10px] tracking-wide ${pairTextClass(pair.label)}`}>
          Validation — {pair.display}
        </p>
        {rows.length === 0 ? (
          <p className="font-sans text-[13px] text-[#737373]">
            No validation rows for this pair yet.
          </p>
        ) : (
          <ValidationTable rows={rows} />
        )}
      </div>
    </div>
  );
}
