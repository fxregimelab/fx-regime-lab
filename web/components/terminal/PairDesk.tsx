// Full pair desk component
'use client';

import { useEffect, useState } from 'react';
import { PAIRS } from '@/lib/constants/pairs';
import { createClient } from '@/lib/supabase/client';
import { getRegimeHistoryForPair } from '@/lib/supabase/queries';
import { useSignalValues } from '@/hooks/useSignalValues';
import { useRegimeCalls } from '@/hooks/useRegimeCalls';
import type { RegimeCall } from '@/lib/types/regime';
import type { SignalValue } from '@/lib/types/signal';

type Props = { strategy: string; pairSlug: string };

/** Normalize URL segment: e.g. `eur-usd` → `eurusd`. */
function normalizePairSlugSegment(raw: string): string {
  return raw.replace(/[^a-z0-9]/gi, '').toLowerCase();
}

/** Map `[pair]` segment to Supabase `pair` column (EURUSD, USDJPY, USDINR). */
function resolvePairLabel(slug: string): string {
  const key = normalizePairSlugSegment(slug);
  const bySlug = PAIRS.find((p) => p.urlSlug === key);
  if (bySlug) return bySlug.label;

  const lettersOnly = slug.replace(/[^a-zA-Z]/g, '').toUpperCase();
  if (lettersOnly.length === 6 && PAIRS.some((p) => p.label === lettersOnly)) {
    return lettersOnly;
  }

  const fromPath = PAIRS.find((p) => p.terminalPath.toLowerCase().endsWith(`/${key}`));
  return fromPath?.label ?? (lettersOnly || slug.toUpperCase());
}

function resolveDisplay(label: string) {
  const m = PAIRS.find((p) => p.label === label);
  return m?.display ?? label;
}

function formatPipelineUtc(iso: string | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  const y = d.getUTCFullYear();
  const mo = String(d.getUTCMonth() + 1).padStart(2, '0');
  const day = String(d.getUTCDate()).padStart(2, '0');
  const h = String(d.getUTCHours()).padStart(2, '0');
  const min = String(d.getUTCMinutes()).padStart(2, '0');
  return `${y}-${mo}-${day} ${h}:${min} UTC`;
}

function formatRateDiff(s: SignalValue | null): string {
  const v = s?.rate_diff_2y;
  if (v == null || Number.isNaN(v)) return '—';
  return v.toFixed(2);
}

function formatPct(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return '—';
  return n.toFixed(0);
}

function formatVol(s: SignalValue | null): string {
  const v = s?.realized_vol_20d;
  if (v == null || Number.isNaN(v)) return '—';
  return v.toFixed(2);
}

function formatComposite(call: RegimeCall | null): string {
  const v = call?.signal_composite;
  if (v == null || Number.isNaN(v)) return '—';
  return v.toFixed(2);
}

function formatImpliedIv(s: SignalValue | null): string {
  const v = s?.implied_vol_30d;
  if (v == null || Number.isNaN(v)) return '—';
  return v.toFixed(2);
}

function confidencePct(call: RegimeCall | null): string {
  const v = call?.confidence;
  if (v == null || Number.isNaN(v)) return '—';
  return `${Math.round(v * 100)}`;
}

function rateArrow(rateSignal: string | null | undefined): string {
  const s = rateSignal?.toUpperCase();
  if (s === 'BULLISH') return '↑';
  if (s === 'BEARISH') return '↓';
  return '→';
}

function cotCrowdingNote(pct: number | null | undefined): string | null {
  if (pct == null || Number.isNaN(pct)) return null;
  if (pct > 85) return 'Crowding: extreme high';
  if (pct < 15) return 'Crowding: extreme low';
  return null;
}

function lastUpdatedLabel(call: RegimeCall | null, signals: SignalValue | null): string {
  const raw = signals?.created_at ?? call?.created_at ?? signals?.date ?? call?.date;
  if (!raw) return '—';
  const d = new Date(raw);
  if (!Number.isNaN(d.getTime())) {
    return d.toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
  }
  return `${raw} UTC`;
}

function isAmberTrendingRegime(call: RegimeCall | null): boolean {
  if (!call?.confidence || call.confidence < 0.55) return false;
  const r = call.regime;
  if (r === 'UNKNOWN' || r === 'NEUTRAL' || r === 'DIRECTIONAL_ONLY') return false;
  return (
    r.includes('STRENGTH') ||
    r.includes('WEAKNESS') ||
    r.includes('PRESSURE') ||
    r === 'VOL_EXPANDING'
  );
}

function DeskSkeleton() {
  return (
    <div className="space-y-4 rounded-md border border-neutral-800 bg-terminal-surface p-6">
      <div className="h-4 w-32 animate-pulse rounded bg-neutral-800" />
      <div className="h-10 w-3/4 max-w-md animate-pulse rounded bg-neutral-800" />
      <div className="h-12 w-24 animate-pulse rounded bg-neutral-800" />
      <div className="h-32 w-full animate-pulse rounded bg-neutral-800" />
    </div>
  );
}

function EmptyDesk({
  display,
  pipelineLine,
}: {
  display: string;
  pipelineLine: string;
}) {
  return (
    <div className="rounded-md border border-neutral-800 bg-[#121212] p-6 shadow-inner">
      <p className="font-mono text-sm leading-relaxed text-neutral-300">
        No data available for {display}
      </p>
      <p className="mt-4 font-mono text-xs text-neutral-500">Last pipeline run: {pipelineLine}</p>
      <p className="mt-2 font-mono text-xs text-neutral-500">Check back after 23:00 UTC</p>
    </div>
  );
}

function SignalRow({
  label,
  value,
  extra,
}: {
  label: string;
  value: string;
  extra?: string | null;
}) {
  return (
    <tr className="border-b border-neutral-800/80 last:border-0">
      <td className="py-2.5 pr-4 font-sans text-xs font-medium text-neutral-400">{label}</td>
      <td className="py-2.5 font-mono text-sm tabular-nums text-neutral-100">{value}</td>
      <td className="py-2.5 pl-2 text-right font-mono text-xs text-neutral-500">{extra ?? ''}</td>
    </tr>
  );
}

export function PairDesk({ strategy, pairSlug }: Props) {
  const label = resolvePairLabel(pairSlug);
  const display = resolveDisplay(label);
  const { row: regime, loading: regLoading, error: regError } = useRegimeCalls(label);
  const { row: signals, loading: sigLoading, error: sigError } = useSignalValues(label);
  const [history, setHistory] = useState<RegimeCall[]>([]);
  const [pipeUtc, setPipeUtc] = useState<string>('—');

  const loading = regLoading || sigLoading;
  const hasAnyData = regime != null || signals != null;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch('/data/pipeline_status.json', { cache: 'no-store' });
        if (!res.ok) return;
        const json = (await res.json()) as { last_run_utc?: string };
        if (!cancelled) setPipeUtc(formatPipelineUtc(json.last_run_utc));
      } catch {
        /* keep — */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const supabase = createClient();
        const { data, error } = await getRegimeHistoryForPair(supabase, label, 7);
        if (cancelled || error || !data) return;
        setHistory(data);
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [label]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <p className="font-mono text-xs text-neutral-500">{strategy}</p>
          <h1 className="font-mono text-xl font-semibold text-neutral-100">{display}</h1>
        </div>
        <DeskSkeleton />
      </div>
    );
  }

  if (!regime && !signals) {
    return (
      <div className="space-y-6">
        <div>
          <p className="font-mono text-xs text-neutral-500">{strategy}</p>
          <h1 className="font-mono text-xl font-semibold text-neutral-100">{display}</h1>
        </div>
        <EmptyDesk display={display} pipelineLine={pipeUtc} />
      </div>
    );
  }

  const cotPct = signals?.cot_percentile;
  const crowding = cotCrowdingNote(cotPct ?? null);
  const iv = signals?.implied_vol_30d;
  const impliedOk = iv != null && typeof iv === 'number' && !Number.isNaN(iv);
  const regimeAccent = isAmberTrendingRegime(regime);

  return (
    <div className="space-y-8">
      <div>
        <p className="font-mono text-xs text-neutral-500">{strategy}</p>
        <h1 className="font-mono text-xl font-semibold text-neutral-100">{display}</h1>
      </div>

      {hasAnyData && (regError || sigError) ? (
        <p className="rounded border border-amber-900/50 bg-amber-950/20 px-3 py-2 font-mono text-xs text-amber-200/90">
          Partial load: {[regError, sigError].filter(Boolean).join(' · ')}
        </p>
      ) : null}

      {!regime && signals ? (
        <p className="font-mono text-xs text-neutral-500">
          Latest regime call row not found; showing signal snapshot only.
        </p>
      ) : null}

      <section className="rounded-md border border-neutral-800 bg-terminal-surface p-6">
        <p
          className={`font-display text-2xl italic leading-snug md:text-3xl ${
            regimeAccent ? 'text-[#e8a045]' : 'text-neutral-100'
          }`}
        >
          {regime?.regime ?? '—'}
        </p>
        <div className="mt-5 flex items-end gap-1">
          <span className="font-mono text-4xl font-medium tabular-nums leading-none text-neutral-100 md:text-5xl">
            {regime ? confidencePct(regime) : '—'}
          </span>
          {confidencePct(regime) !== '—' ? (
            <span className="font-mono text-xl text-neutral-400">%</span>
          ) : null}
        </div>
        <p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-neutral-500">
          Confidence
        </p>

        <div className="mt-8">
          <p className="font-mono text-[10px] uppercase tracking-wider text-neutral-500">
            Signal stack
          </p>
          <table className="mt-3 w-full border-collapse">
            <tbody>
              <SignalRow
                label="Rate differential"
                value={formatRateDiff(signals)}
                extra={rateArrow(regime?.rate_signal)}
              />
              <SignalRow
                label="COT percentile"
                value={formatPct(cotPct ?? null)}
                extra={crowding}
              />
              <SignalRow label="Realized vol" value={formatVol(signals)} />
              <SignalRow label="Signal composite" value={formatComposite(regime)} />
              {impliedOk ? (
                <SignalRow label="Implied vol" value={formatImpliedIv(signals)} />
              ) : (
                <SignalRow label="Implied vol" value="—" extra="N/A" />
              )}
            </tbody>
          </table>
        </div>

        <p className="mt-6 flex items-center gap-2 border-t border-neutral-800 pt-4 font-mono text-[11px] text-neutral-500">
          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" aria-hidden />
          Last updated: {lastUpdatedLabel(regime, signals)}
        </p>
      </section>

      {history.length > 0 ? (
        <section className="rounded-md border border-neutral-800 bg-terminal-surface p-6">
          <h2 className="font-mono text-[10px] uppercase tracking-wider text-neutral-500">
            Regime history (last {history.length} days)
          </h2>
          <ul className="mt-4 space-y-3">
            {history.map((h) => (
              <li
                key={`${h.date}-${h.pair}-${h.id}`}
                className="flex flex-wrap items-baseline justify-between gap-2 border-b border-neutral-800/60 pb-3 font-mono text-xs last:border-0 last:pb-0"
              >
                <span className="text-neutral-500">{h.date}</span>
                <span className="max-w-[min(100%,20rem)] text-right text-neutral-200">{h.regime}</span>
                <span className="tabular-nums text-neutral-400">
                  {h.confidence != null && !Number.isNaN(h.confidence)
                    ? `${Math.round(h.confidence * 100)}%`
                    : '—'}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
