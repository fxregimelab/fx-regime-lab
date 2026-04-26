'use client';

import { ValidationTable } from '@/components/ValidationTable';
import { PAIRS } from '@/lib/mock/data';
import type { PairMeta, ValidationRow } from '@/lib/types';
import { useMemo, useState } from 'react';

type Filter = 'ALL' | PairMeta['label'];

interface Props {
  rows: ValidationRow[];
}

export function PerformanceFilters({ rows }: Props) {
  const [filter, setFilter] = useState<Filter>('ALL');
  const filtered = useMemo(() => {
    if (filter === 'ALL') return rows;
    return rows.filter((r) => r.pair === filter);
  }, [filter, rows]);

  const chips: { id: Filter; label: string }[] = [
    { id: 'ALL', label: 'ALL' },
    ...PAIRS.map((p) => ({ id: p.label, label: p.label })),
  ];

  return (
    <div>
      <div className="mb-6 flex gap-2 overflow-x-auto pb-1">
        {chips.map((c) => (
          <button
            key={c.id}
            type="button"
            onClick={() => setFilter(c.id)}
            className={`shrink-0 rounded-full border px-3 py-1.5 font-mono text-[10px] ${
              filter === c.id
                ? 'border-[#0a0a0a] bg-[#0a0a0a] text-white'
                : 'border-[#e5e5e5] bg-white text-[#737373]'
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>
      <ValidationTable rows={filtered} />
    </div>
  );
}
