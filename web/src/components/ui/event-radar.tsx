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

export type EventRadarTelemetryStatus = {
  invalidation_triggered: boolean;
  telemetry_status: string;
};

type EventRadarProps = {
  pair: string;
  events: MacroEventRow[];
  matrices: EventRiskMatrixRow[];
  telemetryStatus: EventRadarTelemetryStatus | null;
};

function formatNum(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) {
    return 'N/A';
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
        typeof record.execution_note === 'string'
          ? record.execution_note
          : fallback.execution_note,
    };
  } catch {
    return fallback;
  }
}

export function EventRadar({ pair, events, matrices, telemetryStatus }: EventRadarProps) {
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
    <div className="border border-[#111] bg-[#000000] rounded-none shadow-none">
      {crisisMode && (
        <div className="border-b border-[#222] bg-[#0a0804] px-3 py-2 text-[11px] font-medium tracking-widest text-amber-500 tabular-nums">
          [ EVENT PROBABILITIES SUSPENDED: OVERNIGHT MACRO SHIFT DETECTED ]
        </div>
      )}
      <div className="grid grid-cols-[110px_1fr_160px_160px_220px] border-b border-[#111] px-3 py-2">
        <span className="text-[9px] tracking-widest text-[#777]">DATE/TIME</span>
        <span className="text-[9px] tracking-widest text-[#777]">EVENT NAME</span>
        <span className="text-[9px] tracking-widest text-[#777]">FORECAST VS PREV</span>
        <span className="text-[9px] tracking-widest text-[#777]">MIE PROFILE</span>
        <span className="text-[9px] tracking-widest text-[#777]">ASYMMETRY</span>
      </div>

      {rows.length === 0 ? (
        <div className="px-3 py-6 text-[11px] text-[#888] tabular-nums">
          No high-impact event risk rows for {pair}.
        </div>
      ) : (
        rows.map(({ event, matrix, key }) => {
          const isExpanded = expandedKey === key;
          const lowSample = (matrix?.sample_size ?? 0) < 5;
          const asymmetryHot =
            (matrix?.asymmetry_ratio ?? 0) > 2.0 && (matrix?.sample_size ?? 0) >= 5;
          const brief = parseEventBrief(event.ai_brief, pair);

          const mathStrike = crisisMode ? 'text-[#444] line-through' : '';

          return (
            <div key={key} className="border-b border-[#111]">
              <button
                type="button"
                onClick={() => {
                  if (crisisMode) {
                    return;
                  }
                  setExpandedKey(isExpanded ? null : key);
                }}
                className={`grid w-full grid-cols-[110px_1fr_160px_160px_220px] px-3 py-2 text-left rounded-none shadow-none ${
                  crisisMode ? 'cursor-not-allowed' : 'hover:bg-[#050505]'
                }`}
                aria-disabled={crisisMode}
              >
                <span className="text-[11px] text-[#bbb] tabular-nums">{event.date}</span>
                <span className="text-[12px] text-white tabular-nums">{event.event}</span>
                <span className="text-[11px] text-[#888] tabular-nums">
                  {event.category ?? 'N/A'} / {event.impact}
                </span>
                <span className={`text-[11px] tabular-nums ${crisisMode ? mathStrike : 'text-[#888]'}`}>
                  [{matrix?.median_mie_multiplier != null ? ` ${formatNum(matrix.median_mie_multiplier)}x RV20 ` : ' N/A '}]
                </span>
                <span className={`text-[11px] tabular-nums ${crisisMode ? mathStrike : ''}`}>
                  {asymmetryHot ? (
                    <span
                      className={`text-[10px] tracking-widest ${
                        crisisMode
                          ? ''
                          : matrix?.asymmetry_direction === 'UPSIDE'
                            ? 'text-[#22c55e]'
                            : 'text-[#f59e0b]'
                      }`}
                    >
                      [ ASYMMETRIC RISK: {matrix?.asymmetry_direction ?? 'N/A'} ]
                    </span>
                  ) : (
                    <span className={crisisMode ? '' : 'text-[#666]'}>[ NO EDGE ]</span>
                  )}
                </span>
              </button>

              {isExpanded && !crisisMode && (
                <div className="border-t border-[#111] bg-[#030303] px-3 py-3">
                  {lowSample && (
                    <div className="mb-3 border border-[#222] bg-[#130f08] px-2 py-1 text-[11px] tracking-widest text-[#f59e0b] tabular-nums">
                      [ LOW CONFIDENCE SAMPLE (N={matrix?.sample_size ?? 0}) ]
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="border border-[#222] bg-[#000] p-2">
                      <p className="text-[9px] tracking-widest text-[#777]">SAMPLE SIZE</p>
                      <p className="text-[13px] text-white tabular-nums">
                        N = {matrix?.sample_size ?? 0}
                      </p>
                    </div>
                    <div className="border border-[#222] bg-[#000] p-2">
                      <p className="text-[9px] tracking-widest text-[#777]">ASYMMETRY RATIO</p>
                      <p className="text-[13px] text-white tabular-nums">
                        {formatNum(matrix?.asymmetry_ratio)}
                      </p>
                    </div>
                    <div className="border border-[#222] bg-[#000] p-2">
                      <p className="text-[9px] tracking-widest text-[#777]">MEDIAN BEAT RETURN</p>
                      <p
                        className={`text-[13px] tabular-nums ${
                          lowSample ? 'text-[#555]' : 'text-[#22c55e]'
                        }`}
                      >
                        {lowSample ? 'DIMMED (LOW SAMPLE)' : `${formatNum(matrix?.beat_median_return)}%`}
                      </p>
                    </div>
                    <div className="border border-[#222] bg-[#000] p-2">
                      <p className="text-[9px] tracking-widest text-[#777]">MEDIAN MISS RETURN</p>
                      <p
                        className={`text-[13px] tabular-nums ${
                          lowSample ? 'text-[#555]' : 'text-[#ef4444]'
                        }`}
                      >
                        {lowSample ? 'DIMMED (LOW SAMPLE)' : `${formatNum(matrix?.miss_median_return)}%`}
                      </p>
                    </div>
                  </div>
                  <div className="mt-3 grid gap-2">
                    <div className="border border-[#222] bg-[#000] p-2">
                      <p className="text-[9px] tracking-widest text-[#777]">ASYMMETRIC SETUP</p>
                      <p className="text-[11px] text-white tabular-nums">{brief.asymmetric_setup}</p>
                    </div>
                    <div className="border border-[#222] bg-[#000] p-2">
                      <p className="text-[9px] tracking-widest text-[#777]">EXECUTION NOTE</p>
                      <p className="text-[11px] text-white tabular-nums">{brief.execution_note}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
