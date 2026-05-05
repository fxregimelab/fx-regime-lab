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

function todayUtc(): string {
  return new Date().toISOString().slice(0, 10);
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

type RowModel = {
  event: MacroEventRow;
  matrix: EventRiskMatrixRow | null;
  key: string;
};

function impactNameClass(impact: string): string {
  const u = impact.toUpperCase();
  if (u === 'HIGH') return 'text-white font-bold';
  if (u === 'MEDIUM') return 'text-[#888] font-normal';
  return 'text-[#666] font-normal';
}

function NowPulse({ crisisMode }: { crisisMode: boolean }) {
  return (
    <div
      className={`relative my-3 w-full shrink-0 ${crisisMode ? 'bg-[#f59e0b]' : 'bg-[#10b981]'} h-px will-change-[opacity]`}
      style={{
        boxShadow: crisisMode
          ? '0 0 8px rgba(245, 158, 11, 0.5)'
          : '0 0 8px rgba(16, 185, 129, 0.5)',
      }}
      aria-hidden
    />
  );
}

function ExpandedPanel({
  matrix,
  lowSample,
  brief,
}: {
  matrix: EventRiskMatrixRow | null;
  lowSample: boolean;
  brief: EventBriefPayload;
}) {
  return (
    <div className="border-t-[0.5px] border-t-[#111] bg-[#030303] px-3 py-3">
      {lowSample && (
        <div className="mb-3 border border-dashed border-[#333] bg-[#000] px-2 py-1 font-mono text-[11px] tracking-widest text-[#888] tabular-nums">
          [ LOW CONFIDENCE SAMPLE (N={matrix?.sample_size ?? 0}) ]
        </div>
      )}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="border border-[#222] bg-[#000] p-2">
          <p className="text-[9px] tracking-widest text-[#777]">SAMPLE SIZE</p>
          <p className="text-[13px] text-white tabular-nums">N = {matrix?.sample_size ?? 0}</p>
        </div>
        <div className="border border-[#222] bg-[#000] p-2">
          <p className="text-[9px] tracking-widest text-[#777]">ASYMMETRY RATIO</p>
          <p className="text-[13px] text-[#d4d4d4] tabular-nums">{formatNum(matrix?.asymmetry_ratio)}</p>
        </div>
        <div className="border border-[#222] bg-[#000] p-2">
          <p className="text-[9px] tracking-widest text-[#777]">MEDIAN BEAT RETURN</p>
          <p className={`text-[13px] tabular-nums ${lowSample ? 'text-[#555] font-light' : 'text-white font-bold'}`}>
            {lowSample ? 'DIMMED (LOW SAMPLE)' : `${formatNum(matrix?.beat_median_return)}%`}
          </p>
        </div>
        <div className="border border-[#222] bg-[#000] p-2">
          <p className="text-[9px] tracking-widest text-[#777]">MEDIAN MISS RETURN</p>
          <p className={`text-[13px] tabular-nums ${lowSample ? 'text-[#555] font-light' : 'text-[#888] font-normal'}`}>
            {lowSample ? 'DIMMED (LOW SAMPLE)' : `${formatNum(matrix?.miss_median_return)}%`}
          </p>
        </div>
        <div className="col-span-1 border border-[#222] bg-[#000] p-2 sm:col-span-2">
          <p className="text-[9px] tracking-widest text-[#777]">MIE PROBABILITY ZONES</p>
          {matrix?.t1_exhaustion_p16 != null && matrix?.t1_exhaustion_p84 != null ? (
            <div className="mt-1 grid grid-cols-2 gap-2 font-mono text-[10px] tabular-nums text-[#d4d4d4]">
              <div>
                <p className="text-[#888]">1SD ZONE (68%)</p>
                <p className="text-[#e8e8e8]">
                  [{formatNum(matrix.t1_exhaustion_p16)}% to {formatNum(matrix.t1_exhaustion_p84)}%]
                </p>
              </div>
              <div>
                <p className="text-[#888]">2SD EXHAUSTION ZONE</p>
                <p className="text-[#f59e0b]">
                  [{formatNum(matrix.t1_exhaustion_p2_5)}% to {formatNum(matrix.t1_exhaustion_p97_5)}%]
                </p>
              </div>
            </div>
          ) : (
            <p className="mt-1 font-mono text-[10px] text-[#555] tabular-nums">DATA UNAVAILABLE</p>
          )}
        </div>
      </div>
      <div className="mt-3 grid gap-2">
        <div className="border border-[#222] bg-[#000] p-2">
          <p className="text-[9px] tracking-widest text-[#777]">ASYMMETRIC SETUP</p>
          <p className="text-[11px] text-[#d4d4d4] tabular-nums">{brief.asymmetric_setup}</p>
        </div>
        <div className="border border-[#222] bg-[#000] p-2">
          <p className="text-[9px] tracking-widest text-[#777]">EXECUTION NOTE</p>
          <p className="text-[11px] text-[#d4d4d4] tabular-nums">{brief.execution_note}</p>
        </div>
      </div>
    </div>
  );
}

function EventRow({
  pair,
  rm,
  today,
  crisisMode,
  expandedKey,
  setExpandedKey,
}: {
  pair: string;
  rm: RowModel;
  today: string;
  crisisMode: boolean;
  expandedKey: string | null;
  setExpandedKey: (k: string | null) => void;
}) {
  const { event, matrix, key: rowKey } = rm;
  const isPast = event.date < today;
  const isExpanded = expandedKey === rowKey;
  const lowSample = (matrix?.sample_size ?? 0) < 5;
  const asymmetryHot =
    (matrix?.asymmetry_ratio ?? 0) > 2.0 && (matrix?.sample_size ?? 0) >= 5;
  const brief = parseEventBrief(event.ai_brief, pair);
  const mathStrike = crisisMode ? 'text-[#444] line-through' : '';
  const pastShell = isPast ? 'opacity-30 grayscale' : '';

  return (
    <div className={`border-b-[0.5px] border-b-[#111] ${pastShell}`}>
      <button
        type="button"
        onClick={() => {
          if (crisisMode) return;
          setExpandedKey(isExpanded ? null : rowKey);
        }}
        className={`w-full px-3 py-2 text-left shadow-none ${
          crisisMode ? 'cursor-not-allowed' : 'hover:bg-[#050505]'
        }`}
        aria-disabled={crisisMode}
      >
        <div className="hidden w-full grid-cols-[110px_1fr_160px_160px_220px] md:grid">
          <span className="text-[11px] text-[#888] tabular-nums">{event.date}</span>
          <span className={`text-[12px] tabular-nums ${impactNameClass(event.impact)}`}>{event.event}</span>
          <span className="text-[11px] text-[#666] tabular-nums">
            {event.category ?? 'N/A'} / {event.impact}
          </span>
          <span className={`text-[11px] tabular-nums ${crisisMode ? mathStrike : 'text-[#888]'}`}>
            [
            {matrix?.median_mie_multiplier != null ? ` ${formatNum(matrix.median_mie_multiplier)}x RV20 ` : ' N/A '}
            ]
          </span>
          <span className={`text-[11px] tabular-nums ${crisisMode ? mathStrike : ''}`}>
            {asymmetryHot ? (
              <span className="text-[10px] font-bold tracking-widest text-white">
                [ ASYMMETRIC RISK: {matrix?.asymmetry_direction ?? 'N/A'} ]
              </span>
            ) : (
              <span className={crisisMode ? '' : 'text-[#666]'}>[ NO EDGE ]</span>
            )}
          </span>
        </div>

        <div className="flex flex-col gap-1 md:hidden">
          <span className="font-mono text-[10px] text-[#666] tabular-nums">{event.date}</span>
          <span className={`font-mono text-[12px] tabular-nums ${impactNameClass(event.impact)}`}>
            {event.event}
          </span>
          <span className={`font-mono text-[10px] tabular-nums ${crisisMode ? mathStrike : 'text-[#777]'}`}>
            {event.category ?? 'N/A'} / {event.impact} · [
            {matrix?.median_mie_multiplier != null ? `${formatNum(matrix.median_mie_multiplier)}x` : 'N/A'}]
          </span>
          <span className={`font-mono text-[10px] tabular-nums ${crisisMode ? mathStrike : ''}`}>
            {asymmetryHot ? (
              <span className="font-bold tracking-widest text-white">
                [ ASYMMETRIC: {matrix?.asymmetry_direction ?? 'N/A'} ]
              </span>
            ) : (
              <span className="text-[#666]">[ NO EDGE ]</span>
            )}
          </span>
        </div>
      </button>

      {isExpanded && !crisisMode && (
        <ExpandedPanel matrix={matrix} lowSample={lowSample} brief={brief} />
      )}
    </div>
  );
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

  const rows: RowModel[] = useMemo(() => {
    const filtered = events
      .filter((ev) => ev.pairs.includes(pair))
      .map((ev) => ({
        event: ev,
        matrix: matrixMap.get(`${ev.date}|${ev.event}`) ?? null,
        key: `${ev.date}|${ev.event}`,
      }));
    filtered.sort((a, b) => {
      const d = a.event.date.localeCompare(b.event.date);
      if (d !== 0) return d;
      return a.event.event.localeCompare(b.event.event);
    });
    return filtered;
  }, [events, matrixMap, pair]);

  const t = todayUtc();
  const past = rows.filter((r) => r.event.date < t);
  const todayRows = rows.filter((r) => r.event.date === t);
  const future = rows.filter((r) => r.event.date > t);

  const rowProps = {
    pair,
    today: t,
    crisisMode,
    expandedKey,
    setExpandedKey,
  };

  return (
    <div className="border border-[#111] bg-[#000000] shadow-none">
      {crisisMode && (
        <div className="border-b border-[#222] bg-[#0a0804] px-3 py-2 text-[11px] font-medium tracking-widest text-[#f59e0b] tabular-nums">
          [ EVENT PROBABILITIES SUSPENDED: OVERNIGHT MACRO SHIFT DETECTED ]
        </div>
      )}
      <div className="hidden grid-cols-[110px_1fr_160px_160px_220px] border-b-[0.5px] border-b-[#111] px-3 py-2 md:grid">
        <span className="text-[9px] tracking-widest text-[#777]">DATE/TIME</span>
        <span className="text-[9px] tracking-widest text-[#777]">EVENT NAME</span>
        <span className="text-[9px] tracking-widest text-[#777]">FORECAST VS PREV</span>
        <span className="text-[9px] tracking-widest text-[#777]">MIE PROFILE</span>
        <span className="text-[9px] tracking-widest text-[#777]">ASYMMETRY</span>
      </div>

      {rows.length === 0 ? (
        <div className="px-3 py-6 text-[11px] text-[#888] tabular-nums">
          No event risk rows for {pair}.
        </div>
      ) : (
        <>
          <div className="relative hidden md:block">
            <div className="border-l-[0.5px] border-[#222] pl-3">
              {past.map((rm) => (
                <EventRow key={rm.key} {...rowProps} rm={rm} />
              ))}
              <NowPulse crisisMode={crisisMode} />
              {todayRows.map((rm) => (
                <EventRow key={rm.key} {...rowProps} rm={rm} />
              ))}
              {future.map((rm) => (
                <EventRow key={rm.key} {...rowProps} rm={rm} />
              ))}
            </div>
          </div>

          <div className="md:hidden">
            {past.length > 0 ? (
              <>
                <p className="px-3 py-2 font-mono text-[9px] tracking-[0.2em] text-[#555]">[ PAST ]</p>
                {past.map((rm) => (
                  <EventRow key={rm.key} {...rowProps} rm={rm} />
                ))}
              </>
            ) : null}
            <div className="px-3">
              <NowPulse crisisMode={crisisMode} />
            </div>
            {todayRows.length > 0 ? (
              <>
                <p className="px-3 py-2 font-mono text-[9px] tracking-[0.2em] text-[#666]">[ TODAY ]</p>
                {todayRows.map((rm) => (
                  <EventRow key={rm.key} {...rowProps} rm={rm} />
                ))}
              </>
            ) : null}
            {future.length > 0 ? (
              <>
                <p className="px-3 py-2 font-mono text-[9px] tracking-[0.2em] text-[#666]">[ FUTURE ]</p>
                {future.map((rm) => (
                  <EventRow key={rm.key} {...rowProps} rm={rm} />
                ))}
              </>
            ) : null}
          </div>
        </>
      )}
    </div>
  );
}
