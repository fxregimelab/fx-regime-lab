// Full signal stack display
'use client';

import type { SignalValue } from '@/lib/types/signal';

type Props = { values: SignalValue | null; loading?: boolean };

export function SignalDepth({ values, loading }: Props) {
  if (loading) {
    return <p className="font-mono text-xs text-neutral-500">Loading signals…</p>;
  }
  if (!values) {
    return <p className="font-mono text-xs text-neutral-500">No signal row for this pair/date.</p>;
  }
  const rows: [string, string | number | null | undefined][] = [
    ['Spot', values.spot],
    ['Realized vol 5d', values.realized_vol_5d],
    ['Implied vol 30d', values.implied_vol_30d],
    ['COT percentile', values.cot_percentile],
  ];
  return (
    <div className="rounded-md border border-neutral-800 bg-black/40 p-3">
      <h3 className="font-mono text-xs font-semibold text-neutral-300">Signal depth</h3>
      <dl className="mt-2 space-y-1 font-mono text-[11px] text-neutral-400">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-4">
            <dt>{k}</dt>
            <dd className="text-neutral-200">{v ?? '—'}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
