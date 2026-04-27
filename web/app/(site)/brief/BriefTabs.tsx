'use client';

import { BriefPairBlock } from '@/app/(site)/brief/BriefPairBlock';
import type { BriefTabPayload } from '@/app/(site)/brief/brief-types';
import { ValidationTable } from '@/components/ValidationTable';
import { PAIRS } from '@/lib/mock/data';
import { briefTabBottomClass } from '@/lib/pair-styles';
import type { PairMeta, SignalRow, ValidationRow } from '@/lib/types';
import { useState } from 'react';

export type { BriefTabPayload } from '@/app/(site)/brief/brief-types';

type TabKey = 'ALL' | PairMeta['label'];

const TAB_LABELS: TabKey[] = ['ALL', ...PAIRS.map((p) => p.label)];

function labelForTab(tab: TabKey): string {
  if (tab === 'ALL') return 'ALL';
  return PAIRS.find((p) => p.label === tab)?.display ?? tab;
}

export function BriefTabs({
  briefByLabel,
  signalByLabel,
  validationRows,
}: {
  briefByLabel: Record<PairMeta['label'], BriefTabPayload | null>;
  signalByLabel: Record<PairMeta['label'], SignalRow | null>;
  validationRows: ValidationRow[];
}) {
  const [active, setActive] = useState<TabKey>('ALL');
  const visiblePairs =
    active === 'ALL' ? PAIRS : PAIRS.filter((p) => p.label === active);
  const singlePair = active !== 'ALL' ? PAIRS.find((p) => p.label === active) ?? PAIRS[0] : null;
  const rowsForValidation =
    active === 'ALL'
      ? validationRows
      : validationRows.filter((r) => r.pair === singlePair?.label);

  return (
    <div>
      <div className="mb-8 flex overflow-x-auto border-b border-[#e5e5e5]">
        {TAB_LABELS.map((tab) => {
          const isActive = active === tab;
          return (
            <button
              key={tab}
              type="button"
              onClick={() => setActive(tab)}
              className={`border-b-2 px-4 py-3 font-mono text-[11px] font-semibold tracking-widest transition-colors ${
                isActive ? `${briefTabBottomClass(tab)} text-[#0a0a0a]` : 'border-transparent text-[#a0a0a0]'
              }`}
            >
              {labelForTab(tab)}
            </button>
          );
        })}
      </div>

      {active === 'ALL' ? (
        <div className="flex flex-col gap-0">
          {PAIRS.map((p) => (
            <BriefPairBlock
              key={p.label}
              pair={p}
              section={briefByLabel[p.label]}
              signal={signalByLabel[p.label]}
            />
          ))}
        </div>
      ) : (
        <BriefPairBlock
          pair={singlePair!}
          section={briefByLabel[singlePair!.label]}
          signal={signalByLabel[singlePair!.label]}
        />
      )}

      <div className="mt-10">
        <p className="mb-3 font-mono text-[10px] tracking-wide text-[#a0a0a0]">
          Validation — {active === 'ALL' ? 'all pairs' : singlePair?.display}
        </p>
        {rowsForValidation.length === 0 ? (
          <p className="font-sans text-[13px] text-[#737373]">No validation rows for this filter yet.</p>
        ) : (
          <ValidationTable rows={rowsForValidation} />
        )}
      </div>
    </div>
  );
}
