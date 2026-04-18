// Regime-specific chart component
'use client';

import { TimeSeriesChart, type TimePoint } from '@/components/charts/TimeSeriesChart';

type Props = { title: string; series: TimePoint[] };

export function RegimeChart({ title, series }: Props) {
  return (
    <section className="rounded-md border border-neutral-800 bg-terminal-surface p-3">
      <h3 className="mb-2 font-mono text-xs font-medium text-neutral-300">{title}</h3>
      <TimeSeriesChart data={series} />
    </section>
  );
}
