'use client';

import Link from 'next/link';
import { PAIRS } from '@/lib/constants/pairs';
import { ConfidenceBar } from '@/components/regime/ConfidenceBar';
import { Skeleton } from '@/components/ui/Skeleton';
import type { RegimeCall } from '@/lib/types/regime';
import type { SignalValue } from '@/lib/types/signal';
import type { PairLabel } from '@/lib/constants/pairs';

type Props = {
  calls: Record<PairLabel, RegimeCall | null>;
  signals: Record<PairLabel, SignalValue | null>;
  pending: boolean;
};

function formatRateDifferential(s: SignalValue | null): string {
  const v = s?.rate_diff_2y;
  if (v == null || Number.isNaN(v)) return '—';
  return v.toFixed(2);
}

function formatCotPercentile(s: SignalValue | null): string {
  const v = s?.cot_percentile;
  if (v == null || Number.isNaN(v)) return '—';
  return v.toFixed(0);
}

function formatRealizedVol(s: SignalValue | null): string {
  const v = s?.realized_vol_20d;
  if (v == null || Number.isNaN(v)) return '—';
  return v.toFixed(2);
}

function confidencePct(call: RegimeCall | null): string {
  const v = call?.confidence;
  if (v == null || Number.isNaN(v)) return '—';
  return `${Math.round(v * 100)}%`;
}

function PairCardSkeleton() {
  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
      <Skeleton className="h-5 w-24" />
      <Skeleton className="mt-3 h-8 w-full max-w-[200px]" />
      <Skeleton className="mt-4 h-2 w-full" />
      <Skeleton className="mt-2 h-4 w-12" />
      <div className="mt-4 space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-full" />
      </div>
      <Skeleton className="mt-6 h-4 w-32" />
    </div>
  );
}

export function HomePairCards({ calls, signals, pending }: Props) {
  return (
    <div className="mx-auto grid max-w-6xl grid-cols-1 gap-6 px-4 md:grid-cols-3">
      {PAIRS.map((p) => {
        const call = calls[p.label];
        const sig = signals[p.label];
        const showSkeleton = pending && call == null && sig == null;

        if (showSkeleton) {
          return <PairCardSkeleton key={p.label} />;
        }

        return (
          <article
            key={p.label}
            className="flex flex-col rounded-xl border border-neutral-200 bg-white p-6 shadow-sm transition-transform hover:-translate-y-0.5"
          >
            <h2 className="text-lg font-semibold text-neutral-900">{p.display}</h2>
            <p className="mt-2 font-display text-xl italic text-neutral-800">
              {call?.regime ?? '—'}
            </p>
            <div className="mt-4">
              <ConfidenceBar
                value={call?.confidence ?? null}
                tone="light"
                showCaption={false}
                tieredConviction
              />
            </div>
            <p className="mt-2 font-mono text-sm tabular-nums text-neutral-700">{confidencePct(call)}</p>
            <dl className="mt-4 space-y-2 border-t border-neutral-200 pt-4 font-mono text-xs text-neutral-600">
              <div className="flex justify-between gap-2">
                <dt>Rate differential</dt>
                <dd className="tabular-nums text-neutral-900">{formatRateDifferential(sig)}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt>COT percentile</dt>
                <dd className="tabular-nums text-neutral-900">{formatCotPercentile(sig)}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt>Realized vol</dt>
                <dd className="tabular-nums text-neutral-900">{formatRealizedVol(sig)}</dd>
              </div>
            </dl>
            <Link
              href={p.terminalPath}
              className="mt-6 text-sm font-medium text-accent underline decoration-accent underline-offset-4"
            >
              View in terminal →
            </Link>
          </article>
        );
      })}
    </div>
  );
}
