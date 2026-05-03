'use client';

import React from 'react';
import type { DominanceItem, MarkovPayload } from '@/lib/queries';
import { MathInspector } from './math-inspector';
import type { TelemetryAuditPayload } from '@/lib/queries';
import { fmt2 } from './utils';

function ModelInstabilityBadge({ className }: { className?: string }) {
  return (
    <span
      className={`font-mono text-[9px] uppercase tracking-widest text-[#f59e0b] border border-[#f59e0b] bg-transparent px-1.5 py-0.5 whitespace-nowrap ${className ?? ''}`}
      aria-label="Model instability"
    >
      [ MODEL INSTABILITY ]
    </span>
  );
}

export type DeskCardTelemetryRowProps = {
  pairLabel: string;
  spot: number | null | undefined;
  structuralRegime: string;
  confidence: number | null | undefined;
  /** 0–100 apex display (from stored 0–1 apex_score). */
  apexScoreDisplay?: number | null;
  telemetryAudit?: TelemetryAuditPayload | null;
  /** Normalized from snapshot; overrides parsing ``telemetryAudit`` when set. */
  parameterInstability?: boolean;
};

/** Compact row: pair, price, regime, confidence only (no brief / math). */
export function DeskCardTelemetryRow({
  pairLabel,
  spot,
  structuralRegime,
  confidence,
  apexScoreDisplay,
  telemetryAudit,
  parameterInstability,
}: DeskCardTelemetryRowProps) {
  const pct = confidence != null ? Math.round(confidence * 100) : null;
  const modelUnstable =
    parameterInstability ?? Boolean(telemetryAudit?.parameter_instability);
  return (
    <div className="relative border border-[#111] border-t border-t-white/10 bg-[#000000] px-2 py-2 grid grid-cols-[auto_minmax(0,1fr)_auto] gap-x-3 gap-y-1 items-baseline text-[#e8e8e8]">
      {apexScoreDisplay != null ? (
        <span className="absolute top-1.5 right-2 font-mono text-[10px] font-bold tabular-nums text-[#fafafa] z-10">
          {apexScoreDisplay}
        </span>
      ) : null}
      <span className="font-mono text-[11px] tracking-wide shrink-0">{pairLabel}</span>
      <span className="font-mono text-[11px] text-[#f0f0f0] tabular-nums min-w-0 text-right">
        {spot != null ? fmt2(spot) : '—'}
      </span>
      <span className="font-mono text-[10px] text-[#9a9a9a] tabular-nums shrink-0">{pct != null ? `${pct}%` : '—'}</span>
      <div className="relative col-span-3 min-w-0 pr-[168px]">
        <span className="font-mono text-[10px] text-[#b8b8b8] block truncate leading-snug">
          {structuralRegime}
        </span>
        {modelUnstable ? (
          <ModelInstabilityBadge className="absolute top-0 right-0 z-10" />
        ) : null}
      </div>
    </div>
  );
}

type DeskCardProps = {
  variant?: 'default' | 'hero';
  pairDisplay?: string;
  spot?: number | null;
  confidence?: number | null;
  rankJump?: number;
  regimeAge?: number | null;
  /** 0–100 apex display (Rank #1 hero). */
  apexScoreDisplay?: number | null;
  structuralRegime: string;
  invalidationTriggered: boolean;
  telemetryStatus: string;
  dominanceArray: DominanceItem[];
  painIndex: number | null;
  markovProbabilities: MarkovPayload | null;
  aiBrief: string | null;
  telemetryAudit: TelemetryAuditPayload | null;
  /** Normalized from snapshot; falls back to ``telemetry_audit.parameter_instability``. */
  parameterInstability?: boolean;
  /** When set (hero only), shows [ COPY LINKEDIN ALPHA ] → ``/api/linkedin-alpha-hook``. */
  linkedinCardData?: Record<string, unknown> | null;
};

export function DeskCard({
  variant = 'default',
  pairDisplay,
  spot,
  confidence,
  rankJump,
  regimeAge,
  apexScoreDisplay,
  structuralRegime,
  invalidationTriggered,
  telemetryStatus,
  dominanceArray,
  painIndex,
  markovProbabilities,
  aiBrief,
  telemetryAudit,
  parameterInstability,
  linkedinCardData,
}: DeskCardProps) {
  type LiPhase = 'idle' | 'loading' | 'success';
  const [liPhase, setLiPhase] = React.useState<LiPhase>('idle');
  const [liErr, setLiErr] = React.useState<string | null>(null);
  const liSuccessTimer = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  React.useEffect(() => {
    return () => {
      if (liSuccessTimer.current) clearTimeout(liSuccessTimer.current);
    };
  }, []);

  const modelUnstable =
    parameterInstability ?? Boolean(telemetryAudit?.parameter_instability);
  const isOffline = telemetryStatus === 'OFFLINE';
  const isCrisis = invalidationTriggered && !isOffline;
  const toneBorder = isCrisis ? 'border-[#f59e0b]' : 'border-[#111]';
  const muted = isOffline ? 'text-[#666]' : 'text-[#e8e8e8]';
  const top = dominanceArray[0];
  const rest = dominanceArray.slice(1);
  const markovN = markovProbabilities?.weighted_sample_size ?? 0;
  const markovLowSample = markovN < 20;
  const isHero = variant === 'hero';
  const confPct = confidence != null ? Math.round(confidence * 100) : null;

  return (
    <section className={`relative border ${toneBorder} border-t border-t-white/10 bg-[#000000] ${muted}`}>
      {apexScoreDisplay != null ? (
        <span className="absolute top-3 right-3 font-mono text-[12px] font-bold tabular-nums text-[#fafafa] z-10">
          {apexScoreDisplay}
        </span>
      ) : null}
      <div className="border-b border-[#111] px-4 py-3 flex items-center justify-between gap-2">
        <p className="font-mono text-[10px] tracking-widest">
          {isHero ? `[ APEX DESK · ${pairDisplay ?? '—'} ]` : '[ DESK OPEN CARD ]'}
          {regimeAge != null && regimeAge >= 0 ? (
            <span className="text-[#666] tabular-nums"> [ AGE: {regimeAge}D ]</span>
          ) : null}
        </p>
        <MathInspector telemetryAudit={telemetryAudit} />
      </div>
      {isOffline ? (
        <div className="border-b border-[#222] px-4 py-2 font-mono text-[11px] tracking-widest text-[#8a8a8a]">
          [ TELEMETRY OFFLINE ]
        </div>
      ) : null}
      {isCrisis ? (
        <div className="border-b border-[#f59e0b] px-4 py-2 font-mono text-[11px] tracking-widest text-[#f59e0b]">
          [ OVERNIGHT INVALIDATION TRIGGERED ]
        </div>
      ) : null}

      {isHero && !isOffline ? (
        <div className="border-b border-[#111] px-4 py-4 flex flex-wrap items-end justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2 min-w-0">
            {rankJump != null && rankJump > 0 ? (
              <span className="font-mono text-[9px] tracking-widest text-[#ffffff] shrink-0">
                [ RANK JUMP: +{rankJump} ]
              </span>
            ) : null}
            {confPct != null ? (
              <span className="font-mono text-[10px] tabular-nums text-[#8a8a8a] tracking-widest">
                CONF {confPct}%
              </span>
            ) : null}
          </div>
          <p
            className={`font-mono font-extrabold tabular-nums tracking-tight shrink-0 ${
              isCrisis ? 'line-through text-[#f0f0f0] text-[22px]' : 'text-[#f5f5f5] text-[30px] leading-none'
            }`}
          >
            {spot != null ? fmt2(spot) : '—'}
          </p>
        </div>
      ) : null}

      <div className="px-4 py-4">
        <div className="relative pr-[168px] min-h-[14px]">
          <p className="font-mono text-[9px] text-[#777] tracking-widest uppercase">
            STRUCTURAL REGIME
          </p>
          {modelUnstable ? (
            <ModelInstabilityBadge className="absolute top-0 right-0 z-10" />
          ) : null}
        </div>
        <p
          className={`mt-1 font-mono font-extrabold ${
            isHero ? 'text-[28px] leading-tight' : 'text-[20px]'
          } ${isCrisis ? 'line-through text-[#f0f0f0]' : 'text-[#f0f0f0]'}`}
        >
          {structuralRegime}
        </p>
      </div>

      <div className="border-t border-[#111] grid grid-cols-1 md:grid-cols-2">
        <div className="border-r border-[#111] p-4">
          <p className="font-mono text-[9px] tracking-widest text-[#777] mb-2">DOMINANCE ARRAY</p>
          {top ? (
            <div className="border border-[#1c1c1c] p-3 mb-2">
              <p className="font-mono text-[9px] text-[#8e8e8e]">RANK #1</p>
              <p className="font-mono text-[13px] text-[#f3f3f3] mt-1 tabular-nums">
                {top.signal_family.toUpperCase()} ({top.dominance_score.toFixed(3)})
              </p>
            </div>
          ) : null}
          <div className="space-y-2">
            {rest.map((row) => (
              <div key={`${row.rank}-${row.signal_family}`} className="border border-[#141414] p-2">
                <p className="font-mono text-[10px] text-[#d0d0d0]">
                  #{row.rank} {row.signal_family.toUpperCase()}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className={`p-4 ${markovLowSample ? 'opacity-50' : ''}`}>
          <p className="font-mono text-[9px] tracking-widest text-[#777] mb-2">MARKOV PROBABILITIES</p>
          {markovLowSample ? (
            <p className="font-mono text-[10px] tracking-widest text-[#f59e0b] mb-2">
              {'[ LOW CONFIDENCE SAMPLE (N < 20) ]'}
            </p>
          ) : null}
          <p className="font-mono text-[11px] text-[#d0d0d0] tabular-nums">
            CONTINUATION:{' '}
            {markovProbabilities?.continuation_probability != null
              ? `${markovProbabilities.continuation_probability.toFixed(2)}%`
              : 'N/A'}
          </p>
          <div className="mt-2 space-y-1">
            {Object.entries(markovProbabilities?.transitions ?? {}).map(([regime, value]) => (
              <p key={regime} className="font-mono text-[10px] text-[#9f9f9f] tabular-nums">
                {regime}: {value.toFixed(2)}%
              </p>
            ))}
          </div>
        </div>
      </div>

      <div className="border-t border-[#111] px-4 py-3">
        <p className="font-mono text-[9px] tracking-widest text-[#777] mb-2">ASYMMETRY RADAR</p>
        {painIndex != null && painIndex > 80 ? (
          <p className="font-mono text-[11px] text-[#f59e0b] tracking-wide">
            [ ASYMMETRIC SETUP DETECTED: Fundamental vs. Positioning Divergence ]
          </p>
        ) : (
          <p className="font-mono text-[10px] text-[#8a8a8a]">No extreme divergence signal.</p>
        )}
      </div>

      {!isCrisis && !isOffline ? (
        <div className="border-t border-[#111] px-4 py-3">
          <p className="font-mono text-[9px] tracking-widest text-[#777] mb-2">AI BRIEF</p>
          <p className="font-sans text-[13px] text-[#c8c8c8] leading-relaxed">
            {aiBrief ?? 'No desk brief available.'}
          </p>
          {isHero && linkedinCardData && Object.keys(linkedinCardData).length > 0 ? (
            <div className="mt-3">
              <button
                type="button"
                disabled={liPhase === 'loading'}
                onClick={async () => {
                  setLiErr(null);
                  if (liSuccessTimer.current) {
                    clearTimeout(liSuccessTimer.current);
                    liSuccessTimer.current = null;
                  }
                  setLiPhase('loading');
                  try {
                    const res = await fetch('/api/linkedin-alpha-hook', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ cardData: linkedinCardData }),
                    });
                    const j = (await res.json().catch(() => ({}))) as { error?: string; text?: string };
                    if (!res.ok) throw new Error(j.error || 'Request failed');
                    if (!j.text?.trim()) throw new Error('Empty response');
                    await navigator.clipboard.writeText(j.text.trim());
                    setLiPhase('success');
                    liSuccessTimer.current = setTimeout(() => {
                      setLiPhase('idle');
                      liSuccessTimer.current = null;
                    }, 2000);
                  } catch (e) {
                    setLiPhase('idle');
                    setLiErr(e instanceof Error ? e.message : 'Copy failed');
                  }
                }}
                className={`border bg-[#000000] px-2 py-1.5 font-mono text-[9px] tracking-widest cursor-pointer transition-transform disabled:cursor-not-allowed active:scale-[0.98] ${
                  liPhase === 'success'
                    ? 'border-[#10b981] text-[#34d399]'
                    : 'border-[#333] text-[#c8c8c8] hover:border-[#555] hover:text-white'
                } ${liPhase === 'loading' ? 'animate-pulse opacity-70' : ''}`}
              >
                {liPhase === 'loading'
                  ? '[ GENERATING... ]'
                  : liPhase === 'success'
                    ? '[ COPIED! ✓ ]'
                    : '[ COPY LINKEDIN ALPHA ]'}
              </button>
              {liErr ? (
                <p className="mt-2 font-mono text-[9px] text-[#ef4444] m-0">{liErr}</p>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
