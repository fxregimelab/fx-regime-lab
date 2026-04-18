'use client';

import Link from 'next/link';
import { ROUTES } from '@/lib/constants/routes';
import { useValidationHomeStrip } from '@/hooks/useValidationLog';
import type { ValidationHomeStrip } from '@/lib/supabase/queries';
import { Skeleton } from '@/components/ui/Skeleton';

type Props = {
  initialStrip: ValidationHomeStrip | null;
};

function StatBlock({ value, label }: { value: string; label: string }) {
  return (
    <div className="text-center">
      <div className="font-mono text-3xl font-medium tabular-nums text-white md:text-4xl">{value}</div>
      <div className="mt-2 font-sans text-[12px] font-medium uppercase tracking-wide text-neutral-500">
        {label}
      </div>
    </div>
  );
}

function StatBlockSkeleton() {
  return (
    <div className="flex flex-col items-center py-1">
      <Skeleton className="h-10 w-20 bg-neutral-700" />
      <Skeleton className="mt-3 h-3 w-28 bg-neutral-700" />
    </div>
  );
}

export function TrackRecordStrip({ initialStrip }: Props) {
  const { strip, rolling20Display, loading } = useValidationHomeStrip({ initialStrip });
  const waiting = loading && strip == null;

  const daysLogged = strip != null ? String(strip.distinctDates) : '—';
  const predictions = strip != null ? String(strip.totalRows) : '—';
  const accuracy = strip != null ? rolling20Display : '—';

  return (
    <section className="bg-[#1a1a1a] py-12 text-white">
      <div className="mx-auto max-w-6xl px-4">
        <div className="grid grid-cols-2 gap-10 md:grid-cols-4 md:gap-6">
          <StatBlock value="Apr 2026" label="TRACKING SINCE" />
          {waiting ? (
            <StatBlockSkeleton />
          ) : (
            <StatBlock value={daysLogged} label="DAYS LOGGED" />
          )}
          {waiting ? (
            <StatBlockSkeleton />
          ) : (
            <StatBlock value={predictions} label="TOTAL PREDICTIONS" />
          )}
          <div className="text-center">
            {waiting ? (
              <StatBlockSkeleton />
            ) : (
              <StatBlock value={accuracy} label="20-DAY ACCURACY" />
            )}
            <p className="mt-2 font-sans text-[11px] text-neutral-500">
              Directional calls only — NEUTRAL excluded
            </p>
          </div>
        </div>
        <p className="mx-auto mt-10 max-w-3xl text-center text-[13px] leading-relaxed text-neutral-500">
          No backdating. Calls logged at generation time. Outcomes filled next trading day.{' '}
          <Link
            href={ROUTES.performance}
            className="text-accent underline decoration-accent underline-offset-4"
          >
            Full log →
          </Link>
        </p>
      </div>
    </section>
  );
}
