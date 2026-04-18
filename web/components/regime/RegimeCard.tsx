// Regime call card — hero (shell home) or compact (terminal).
'use client';

import type { RegimeCall } from '@/lib/types/regime';
import type { SignalValue } from '@/lib/types/signal';
import { ConfidenceBar } from '@/components/regime/ConfidenceBar';
import { Skeleton } from '@/components/ui/Skeleton';

export type RegimeCardVariant = 'hero' | 'compact';

type Props = {
  call: RegimeCall | null;
  signals: SignalValue | null;
  loading?: boolean;
  variant: RegimeCardVariant;
  /** Display label e.g. "EUR / USD" from PAIRS; falls back to `call.pair`. */
  pairDisplay?: string;
};

/** 2Y rate differential spread (pipeline float on `signals.rate_diff_2y`). */
function formatRateDifferential(s: SignalValue | null): string {
  const v = s?.rate_diff_2y;
  if (v == null || Number.isNaN(v)) return '—';
  return v.toFixed(2);
}

function formatCotPercentile(s: SignalValue | null): string {
  const v = s?.cot_percentile;
  if (v == null || Number.isNaN(v)) return '—';
  return `${v.toFixed(0)}`;
}

function formatRealizedVol(s: SignalValue | null): string {
  const v = s?.realized_vol_20d;
  if (v == null || Number.isNaN(v)) return '—';
  return v.toFixed(2);
}

function formatComposite(call: RegimeCall | null): string {
  const v = call?.signal_composite;
  if (v == null || Number.isNaN(v)) return '—';
  return v.toFixed(2);
}

function confidencePercent(call: RegimeCall | null): string {
  const v = call?.confidence;
  if (v == null || Number.isNaN(v)) return '—';
  return `${Math.round(v * 100)}`;
}

function asOfUtcLabel(call: RegimeCall | null, signals: SignalValue | null): string {
  const raw = signals?.date ?? call?.date;
  if (!raw) return '—';
  const d = new Date(`${raw}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) {
    return `${raw} UTC`;
  }
  const y = d.getUTCFullYear();
  const mo = String(d.getUTCMonth() + 1).padStart(2, '0');
  const day = String(d.getUTCDate()).padStart(2, '0');
  return `${y}-${mo}-${day} UTC`;
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <span className="font-sans text-xs font-medium text-neutral-400">{label}</span>
      <span className="font-mono text-sm tabular-nums text-neutral-100">{value}</span>
    </div>
  );
}

export function RegimeCard({ call, signals, loading, variant, pairDisplay }: Props) {
  if (loading) {
    return (
      <div
        className={
          variant === 'hero'
            ? 'min-h-[320px] rounded-xl bg-[#1a1a1a] p-7'
            : 'min-h-[200px] rounded-md border border-neutral-800 bg-terminal-surface p-4'
        }
      >
        {variant === 'hero' ? (
          <div className="space-y-4">
            <Skeleton className="h-4 w-1/3 max-w-[120px] bg-neutral-700" />
            <Skeleton className="h-10 w-2/3 max-w-[280px] bg-neutral-700" />
            <Skeleton className="h-12 w-24 bg-neutral-700" />
            <Skeleton className="h-2 w-full bg-neutral-700" />
            <div className="space-y-3 pt-4">
              <Skeleton className="h-4 w-full bg-neutral-700" />
              <Skeleton className="h-4 w-full bg-neutral-700" />
              <Skeleton className="h-4 w-4/5 bg-neutral-700" />
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <Skeleton className="h-4 w-1/3 bg-neutral-700" />
            <Skeleton className="h-8 w-2/3 bg-neutral-700" />
            <Skeleton className="h-10 w-full bg-neutral-700" />
          </div>
        )}
      </div>
    );
  }

  if (!call) {
    return (
      <div
        className={
          variant === 'hero'
            ? 'rounded-xl bg-[#1a1a1a] p-7 font-mono text-xs text-neutral-500'
            : 'rounded-md border border-neutral-800 bg-terminal-surface p-4 font-mono text-xs text-neutral-500'
        }
      >
        No regime call for this pair.
      </div>
    );
  }

  const pairLine = pairDisplay ?? call.pair;
  const pct = confidencePercent(call);

  if (variant === 'hero') {
    return (
      <section className="rounded-xl bg-[#1a1a1a] p-7 text-neutral-100">
        <p className="font-sans text-sm font-medium text-neutral-400">{pairLine}</p>
        <p className="mt-2 font-display text-2xl italic leading-tight text-neutral-100 md:text-3xl">
          {call.regime}
        </p>
        <div className="mt-6 flex items-end gap-1">
          {pct === '—' ? (
            <span className="font-mono text-4xl font-medium tabular-nums leading-none md:text-5xl">—</span>
          ) : (
            <>
              <span className="font-mono text-4xl font-medium tabular-nums leading-none md:text-5xl">
                {pct}
              </span>
              <span className="font-mono text-xl text-neutral-300">%</span>
            </>
          )}
        </div>
        <p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-neutral-500">Confidence</p>
        <div className="my-6 border-t border-neutral-700" />
        <div className="divide-y divide-neutral-800 space-y-0 [&>div]:py-3">
          <MetricRow label="Rate differential" value={formatRateDifferential(signals)} />
          <MetricRow label="COT percentile" value={formatCotPercentile(signals)} />
          <MetricRow label="Realized vol" value={formatRealizedVol(signals)} />
          <MetricRow label="Signal composite" value={formatComposite(call)} />
        </div>
        <div className="mt-6 flex items-center gap-2 border-t border-neutral-700 pt-4">
          <span className="h-2 w-2 shrink-0 rounded-full bg-emerald-500" aria-hidden />
          <p className="font-mono text-[11px] text-neutral-500">As of {asOfUtcLabel(call, signals)}</p>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-md border border-neutral-800 bg-terminal-surface p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-mono text-sm text-neutral-200">{pairLine}</span>
      </div>
      <p className="mt-2 font-display text-lg italic text-neutral-100">{call.regime}</p>
      <div className="mt-4">
        <ConfidenceBar value={call.confidence} tone="dark" />
      </div>
      <div className="mt-4 divide-y divide-neutral-800 border-t border-neutral-800 pt-3 [&>div]:py-2">
        <MetricRow label="Rate differential" value={formatRateDifferential(signals)} />
        <MetricRow label="COT percentile" value={formatCotPercentile(signals)} />
        <MetricRow label="Realized vol" value={formatRealizedVol(signals)} />
        <MetricRow label="Signal composite" value={formatComposite(call)} />
      </div>
      {call.primary_driver ? (
        <p className="mt-3 text-xs text-neutral-400">{call.primary_driver}</p>
      ) : null}
      <div className="mt-4 flex items-center gap-2 border-t border-neutral-800 pt-3">
        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" aria-hidden />
        <p className="font-mono text-[10px] text-neutral-500">As of {asOfUtcLabel(call, signals)}</p>
      </div>
    </section>
  );
}
