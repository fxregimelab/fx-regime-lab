'use client';

import { useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { getValidationLog } from '@/lib/supabase/queries';
import type { ValidationHomeStrip } from '@/lib/supabase/queries';
import { useValidationHomeStrip } from '@/hooks/useValidationLog';
import { ValidationTable } from '@/components/regime/ValidationTable';
import { Skeleton } from '@/components/ui/Skeleton';
import type { ValidationRow } from '@/lib/types/validation';

type Props = {
  initialStrip: ValidationHomeStrip | null;
  initialRows: ValidationRow[];
};

function StatBlock({ value, label }: { value: string; label: string }) {
  return (
    <div className="text-center">
      <div className="font-mono text-2xl font-medium tabular-nums text-neutral-900 md:text-3xl">{value}</div>
      <div className="mt-2 font-sans text-[11px] font-medium uppercase tracking-wide text-neutral-500">
        {label}
      </div>
    </div>
  );
}

function StatSkeleton() {
  return (
    <div className="flex flex-col items-center py-1">
      <Skeleton className="h-9 w-16 bg-neutral-200" />
      <Skeleton className="mt-3 h-3 w-24 bg-neutral-200" />
    </div>
  );
}

export function PerformanceClient({ initialStrip, initialRows }: Props) {
  const { strip, rolling20Display, loading: stripLoading } = useValidationHomeStrip({ initialStrip });
  const [rows, setRows] = useState<ValidationRow[]>(initialRows);
  const [tableLoading, setTableLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setTableLoading(true);
      try {
        const supabase = createClient();
        const { data, error } = await getValidationLog(supabase, { limit: 500 });
        if (!cancelled && !error && data) setRows(data);
      } finally {
        if (!cancelled) setTableLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const waitingStrip = stripLoading && strip == null;
  const daysLogged = strip != null ? String(strip.distinctDates) : '—';
  const predictions = strip != null ? String(strip.totalRows) : '—';
  const accuracy = rolling20Display;

  return (
    <>
      <section className="mt-10 rounded-xl border border-neutral-200 bg-white p-8 shadow-sm">
        <h2 className="font-sans text-lg font-semibold text-neutral-900">Track record at a glance</h2>
        <p className="mt-1 text-sm text-neutral-600">
          Same headline metrics as the home page strip. All pairs; no backdating.
        </p>
        <div className="mt-8 grid grid-cols-2 gap-8 md:grid-cols-4 md:gap-6">
          <StatBlock value="Apr 2026" label="TRACKING SINCE" />
          {waitingStrip ? (
            <StatSkeleton />
          ) : (
            <StatBlock value={daysLogged} label="DAYS LOGGED" />
          )}
          {waitingStrip ? (
            <StatSkeleton />
          ) : (
            <StatBlock value={predictions} label="TOTAL PREDICTIONS" />
          )}
          {waitingStrip ? (
            <StatSkeleton />
          ) : (
            <StatBlock value={accuracy} label="20-DAY ACCURACY" />
          )}
        </div>
      </section>

      <section className="mt-12">
        <h2 className="font-sans text-lg font-semibold text-neutral-900">Validation log</h2>
        <p className="mt-1 text-sm text-neutral-600">
          Recent rows from <span className="font-mono">validation_log</span> (newest first, up to 500).
        </p>
        <div className="mt-6">
          <ValidationTable rows={rows} loading={tableLoading && rows.length === 0} variant="shell" />
        </div>
      </section>
    </>
  );
}
