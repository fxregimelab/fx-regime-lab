'use client';

import { useEffect, useMemo, useState } from 'react';
import type { Database } from '@/lib/supabase/database.types';

type MacroEventRow = Database['public']['Tables']['macro_events']['Row'];
type EventRiskMatrixRow = Database['public']['Tables']['event_risk_matrices']['Row'];

type EventBriefPayload = {
  volatility_profile: string;
  asymmetric_setup: string;
  execution_note: string;
};

export type ConvexityRadarTelemetryStatus = {
  invalidation_triggered: boolean;
  telemetry_status: string;
};

type ConvexityRadarProps = {
  pair: string;
  events: MacroEventRow[];
  matrices: EventRiskMatrixRow[];
  telemetryStatus: ConvexityRadarTelemetryStatus | null;
  /** Latest spot for pip-scale tail tooltip (optional). */
  quoteSpot?: number | null;
};

function formatNum(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) {
    return '—';
  }
  return value.toFixed(digits);
}

function parseEventBrief(aiBrief: string | null, pair: string): EventBriefPayload {
  const fallback: EventBriefPayload = {
    volatility_profile: 'Volatility profile unavailable.',
    asymmetric_setup: 'Asymmetric setup unavailable.',
    execution_note: 'Execution note unavailable.',
  };
  if (!aiBrief) {
    return fallback;
  }
  try {
    const parsed: unknown = JSON.parse(aiBrief);
    if (!parsed || typeof parsed !== 'object') {
      return fallback;
    }
    const record = parsed as Record<string, unknown>;
    const pairPayload = record[pair];
    if (typeof pairPayload === 'string') {
      try {
        const nested = JSON.parse(pairPayload) as Partial<EventBriefPayload>;
        return {
          volatility_profile:
            typeof nested.volatility_profile === 'string'
              ? nested.volatility_profile
              : fallback.volatility_profile,
          asymmetric_setup:
            typeof nested.asymmetric_setup === 'string'
              ? nested.asymmetric_setup
              : fallback.asymmetric_setup,
          execution_note:
            typeof nested.execution_note === 'string'
              ? nested.execution_note
              : fallback.execution_note,
        };
      } catch {
        return fallback;
      }
    }
    return {
      volatility_profile:
        typeof record.volatility_profile === 'string'
          ? record.volatility_profile
          : fallback.volatility_profile,
      asymmetric_setup:
        typeof record.asymmetric_setup === 'string'
          ? record.asymmetric_setup
          : fallback.asymmetric_setup,
      execution_note:
        typeof record.execution_note === 'string' ? record.execution_note : fallback.execution_note,
    };
  } catch {
    return fallback;
  }
}

function clamp(n: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, n));
}

function pctReturnToPips(
  pct: number | null | undefined,
  spot: number | null | undefined,
  pair: string,
): number | null {
  if (pct == null || !Number.isFinite(pct) || spot == null || !Number.isFinite(spot) || spot === 0) {
    return null;
  }
  const jpy = pair.includes('JPY');
  const move = (Math.abs(pct) / 100) * spot;
  return jpy ? move / 0.01 : move / 0.0001;
}

function ExhaustionZonesBar({
  p25,
  p16,
  p84,
  p975,
  tailP95,
  spot,
  pairSymbol,
}: {
  p25: number;
  p16: number;
  p84: number;
  p975: number;
  tailP95: number | null | undefined;
  spot: number | null | undefined;
  pairSymbol: string;
}) {
  const lo = p25;
  const hi = p975;
  const span = hi - lo;
  if (!(span > 0) || !Number.isFinite(span)) {
    return null;
  }
  const pct = (x: number) => clamp(((x - lo) / span) * 100, 0, 100);
  const innerL = pct(p16);
  const innerR = pct(p84);
  const zeroX = pct(0);
  const tailPips = pctReturnToPips(tailP95, spot, pairSymbol);
  const tailTooltip =
    tailPips != null
      ? `Tail Risk (95th Pctile): ${tailPips.toFixed(1)} pips. Warning: Historically, 5% of moves exceeded this zone.`
      : tailP95 != null && Number.isFinite(tailP95)
        ? `Tail Risk (95th Pctile): ${tailP95.toFixed(2)}% return. Warning: Historically, 5% of moves exceeded this zone.`
        : undefined;

  return (
    <div className="mt-4 relative">
      {tailP95 != null && Number.isFinite(tailP95) ? (
        <div
          className="pointer-events-none absolute -inset-[2px] border-2 border-[var(--color-bearish)] animate-tail-risk-ring z-10 rounded-none"
          aria-hidden
        />
      ) : null}
      <div title={tailTooltip}>
        <p className="mb-2 font-mono text-[9px] tracking-[0.2em] text-[#777] tabular-nums">
          PROBABILISTIC T+1 EXHAUSTION · RETURN %
        </p>
        <div className="relative h-12 w-full border border-[#141414] bg-[#000000]">
        {/* Outer (≈95%) zone */}
        <div
          className="pointer-events-none absolute inset-[6px] rounded-none"
          style={{
            background:
              'linear-gradient(90deg, #3b82f622 0%, #a855f722 35%, #eab30822 65%, #ef444422 100%)',
          }}
          aria-hidden
        />
        {/* Inner (≈68%) band */}
        <div
          className="pointer-events-none absolute inset-y-[10px] rounded-none"
          style={{
            left: `${innerL}%`,
            width: `${Math.max(innerR - innerL, 0.35)}%`,
            backgroundColor: '#22c55e22',
            boxShadow: 'inset 0 0 0 1px #22c55e33',
          }}
          aria-hidden
        />
        {/* 0% reference */}
        <div
          className="pointer-events-none absolute top-1 bottom-1 w-px bg-[#ffffff55]"
          style={{ left: `${zeroX}%`, transform: 'translateX(-50%)' }}
          aria-hidden
        />
      </div>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-x-4 gap-y-1 font-mono text-[9px] text-[#666] tabular-nums">
        <span>
          <span className="text-[#555]">P2.5 </span>
          {p25.toFixed(2)}%
        </span>
        <span className="text-[#888]">INNER 68% · OUTER 95%</span>
        <span>
          <span className="text-[#555]">P97.5 </span>
          {p975.toFixed(2)}%
        </span>
      </div>
      </div>
    </div>
  );
}

export function ConvexityRadar({
  pair,
  events,
  matrices,
  telemetryStatus,
  quoteSpot,
}: ConvexityRadarProps) {
  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const crisisMode = Boolean(telemetryStatus?.invalidation_triggered);

  useEffect(() => {
    if (crisisMode) {
      setExpandedKey(null);
    }
  }, [crisisMode]);

  const matrixMap = useMemo(() => {
    const map = new Map<string, EventRiskMatrixRow>();
    for (const matrix of matrices) {
      map.set(`${matrix.date}|${matrix.event_name}`, matrix);
    }
    return map;
  }, [matrices]);

  const rows = useMemo(
    () =>
      events
        .filter((ev) => ev.impact === 'HIGH' && ev.pairs.includes(pair))
        .map((ev) => ({
          event: ev,
          matrix: matrixMap.get(`${ev.date}|${ev.event}`) ?? null,
          key: `${ev.date}|${ev.event}`,
        })),
    [events, matrixMap, pair],
  );

  return (
    <div className="rounded-none border border-[#111] bg-[#000000] shadow-none">
      {crisisMode && (
        <div className="border-b border-[#1f1f1f] bg-[#0a0804] px-3 py-2 font-mono text-[11px] font-medium tracking-widest text-amber-500 tabular-nums">
          [ EVENT PROBABILITIES SUSPENDED: OVERNIGHT MACRO SHIFT DETECTED ]
        </div>
      )}

      {rows.length === 0 ? (
        <div className="px-4 py-8 font-mono text-[11px] text-[#888] tabular-nums">
          No high-impact convexity rows for {pair}.
        </div>
      ) : (
        <ul className="divide-y divide-[#111]">
          {rows.map(({ event, matrix, key }) => {
            const isExpanded = expandedKey === key;
            const n = matrix?.sample_size ?? 0;
            const lowSample = n < 5;
            const asymmetryHot =
              (matrix?.asymmetry_ratio ?? 0) > 2.0 && n >= 5 && !lowSample;
            const brief = parseEventBrief(event.ai_brief, pair);
            const mathStrike = crisisMode ? 'text-[#444] line-through' : '';

            const p25 = matrix?.t1_exhaustion_p2_5;
            const p16 = matrix?.t1_exhaustion_p16;
            const p84 = matrix?.t1_exhaustion_p84;
            const p975 = matrix?.t1_exhaustion_p97_5;
            const tailP95 = matrix?.t1_tail_risk_p95;
            const showExhaustion =
              !lowSample &&
              p25 != null &&
              p16 != null &&
              p84 != null &&
              p975 != null &&
              Number.isFinite(p25) &&
              Number.isFinite(p16) &&
              Number.isFinite(p84) &&
              Number.isFinite(p975);

            return (
              <li key={key} className="bg-[#000000]">
                <button
                  type="button"
                  onClick={() => {
                    if (crisisMode) {
                      return;
                    }
                    setExpandedKey(isExpanded ? null : key);
                  }}
                  className={`flex w-full flex-col gap-2 px-4 py-3 text-left sm:flex-row sm:items-center sm:justify-between sm:gap-4 ${
                    crisisMode ? 'cursor-not-allowed' : 'hover:bg-[#050505]'
                  } rounded-none shadow-none`}
                  aria-expanded={isExpanded}
                  aria-disabled={crisisMode}
                >
                  <div className="min-w-0 flex-1">
                    <div className="font-mono text-[11px] text-[#888] tabular-nums">{event.date}</div>
                    <div className="truncate font-mono text-[13px] text-white tabular-nums">{event.event}</div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                    <span
                      className={`border border-[#1a1a1a] px-2 py-1 font-mono text-[10px] tracking-widest tabular-nums text-[#aaa] ${mathStrike}`}
                    >
                      MIE×RV20 {matrix?.median_mie_multiplier != null ? formatNum(matrix.median_mie_multiplier) : '—'}
                    </span>
                    {lowSample ? (
                      <span className="border border-[#333] bg-[#eab30822] px-2 py-1 font-mono text-[10px] tracking-widest text-[#d4d4d4] tabular-nums">
                        [ N &lt; 5 · VOL ONLY ]
                      </span>
                    ) : asymmetryHot ? (
                      <span className="border border-[var(--color-bearish)] bg-[#f8717122] px-2 py-1 font-mono text-[10px] font-semibold tracking-widest text-[#fecaca] tabular-nums shadow-none">
                        [ ASYMMETRIC RISK ]
                      </span>
                    ) : (
                      <span className="font-mono text-[10px] tracking-widest text-[#555] tabular-nums">
                        [ SYMMETRIC ]
                      </span>
                    )}
                  </div>
                </button>

                {isExpanded && !crisisMode && (
                  <div className="border-t border-[#111] bg-[#000000] px-4 pb-4 pt-2">
                    {lowSample && (
                      <div className="mb-4 border border-[#2a2214] bg-[#ef444422] px-3 py-2 font-mono text-[11px] tracking-widest text-[#fcd34d] tabular-nums">
                        N &lt; 5 · VOLATILITY PROFILE ONLY (NO DIRECTIONAL BUCKETS)
                      </div>
                    )}

                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="border border-[#141414] bg-[#000000] px-3 py-2">
                        <p className="font-mono text-[9px] tracking-widest text-[#666]">SAMPLE (REGIME-MATCHED)</p>
                        <p className="font-mono text-[14px] text-white tabular-nums">N = {n}</p>
                      </div>
                      <div className="border border-[#141414] bg-[#000000] px-3 py-2">
                        <p className="font-mono text-[9px] tracking-widest text-[#666]">MEDIAN MIE MULTIPLIER</p>
                        <p className={`font-mono text-[14px] tabular-nums text-white ${mathStrike}`}>
                          {matrix?.median_mie_multiplier != null ? formatNum(matrix.median_mie_multiplier) : '—'}
                        </p>
                      </div>
                    </div>

                    {!lowSample && (
                      <>
                        <div className="mt-4 grid gap-3 sm:grid-cols-2">
                          <div className="border border-[#141414] bg-[#000000] px-3 py-2">
                            <p className="font-mono text-[9px] tracking-widest text-[#666]">MEDIAN T+1 · BEAT</p>
                            <p className="font-mono text-[14px] tabular-nums text-[var(--color-bullish)]">
                              {formatNum(matrix?.beat_median_return)}%
                            </p>
                          </div>
                          <div className="border border-[#141414] bg-[#000000] px-3 py-2">
                            <p className="font-mono text-[9px] tracking-widest text-[#666]">MEDIAN T+1 · MISS</p>
                            <p className="font-mono text-[14px] tabular-nums text-[var(--color-bearish)]">
                              {formatNum(matrix?.miss_median_return)}%
                            </p>
                          </div>
                          <div className="border border-[#141414] bg-[#000000] px-3 py-2">
                            <p className="font-mono text-[9px] tracking-widest text-[#666]">MEDIAN T+1 · IN-LINE</p>
                            <p className="font-mono text-[14px] tabular-nums text-[#eab308]">
                              {formatNum(matrix?.inline_median_return)}%
                            </p>
                          </div>
                          <div className="border border-[#141414] bg-[#000000] px-3 py-2">
                            <p className="font-mono text-[9px] tracking-widest text-[#666]">ASYMMETRY RATIO</p>
                            <p className="font-mono text-[14px] tabular-nums text-white">
                              {formatNum(matrix?.asymmetry_ratio)}
                            </p>
                          </div>
                        </div>

                        {showExhaustion && (
                          <ExhaustionZonesBar
                            p25={p25}
                            p16={p16}
                            p84={p84}
                            p975={p975}
                            tailP95={tailP95}
                            spot={quoteSpot}
                            pairSymbol={pair}
                          />
                        )}
                      </>
                    )}

                    <div className="mt-4 space-y-2 border border-[#141414] bg-[#000000] px-3 py-2">
                      <p className="font-mono text-[9px] tracking-widest text-[#666]">VOLATILITY PROFILE</p>
                      <p className="font-mono text-[11px] leading-relaxed text-[#ccc] tabular-nums">
                        {brief.volatility_profile}
                      </p>
                    </div>
                    {!lowSample && (
                      <div className="mt-2 space-y-2 border border-[#141414] bg-[#000000] px-3 py-2">
                        <p className="font-mono text-[9px] tracking-widest text-[#666]">ASYMMETRIC SETUP</p>
                        <p className="font-mono text-[11px] leading-relaxed text-[#ccc] tabular-nums">
                          {brief.asymmetric_setup}
                        </p>
                        <p className="font-mono text-[9px] tracking-widest text-[#666]">EXECUTION</p>
                        <p className="font-mono text-[11px] leading-relaxed text-[#ccc] tabular-nums">
                          {brief.execution_note}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
