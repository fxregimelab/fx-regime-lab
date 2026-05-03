'use client';

import { useState } from 'react';
import { ConvexityRadar } from '@/components/ui/convexity-radar';
import {
  useEventRiskMatrices,
  useLatestSignals,
  useTelemetryStatus,
  useUpcomingMacroEvents,
  useUniverse,
} from '@/lib/queries';

/** Shared body for event radar (terminal + legacy shell). */
export function ConvexityRadarPageContent() {
  const [selectedPair, setSelectedPair] = useState<string>('EURUSD');
  const eventsQ = useUpcomingMacroEvents();
  const matricesQ = useEventRiskMatrices(selectedPair);
  const signalsQ = useLatestSignals();
  const telemetryQ = useTelemetryStatus(selectedPair);
  const universeQ = useUniverse();
  const trackedPairs = universeQ.data ?? [];
  const events = eventsQ.data ?? [];
  const matrices = matricesQ.data ?? [];
  const quoteSpot =
    (signalsQ.data?.[selectedPair]?.spot as number | null | undefined) ?? null;

  return (
    <section className="w-full px-6 md:px-8 py-10">
      <h1 className="font-sans text-3xl font-bold mb-2 text-white">Convexity Radar</h1>
      <p className="font-mono text-[11px] text-[#8a8a8a] tracking-widest mb-6">
        MIE · T+1 EXHAUSTION BANDS · REGIME-CONDITIONED ASYMMETRY
      </p>

      <div className="mb-4 flex gap-2">
        {trackedPairs.map((pair) => (
          <button
            key={pair}
            type="button"
            onClick={() => setSelectedPair(pair)}
            className={`border px-3 py-1 text-[10px] tracking-widest tabular-nums rounded-none shadow-none ${
              selectedPair === pair
                ? 'border-[#222] bg-[#111] text-white'
                : 'border-[#111] bg-[#000] text-[#888]'
            }`}
          >
            {pair}
          </button>
        ))}
      </div>

      {eventsQ.isPending || matricesQ.isPending || signalsQ.isPending ? (
        <div className="border border-[#111] bg-[#000] px-4 py-8">
          <span className="font-mono text-[11px] text-[#666] tabular-nums">LOADING CONVEXITY RADAR...</span>
        </div>
      ) : (
        <ConvexityRadar
          pair={selectedPair}
          events={events}
          matrices={matrices}
          quoteSpot={quoteSpot}
          telemetryStatus={
            telemetryQ.data
              ? {
                  invalidation_triggered: telemetryQ.data.invalidation_triggered,
                  telemetry_status: telemetryQ.data.telemetry_status,
                }
              : null
          }
        />
      )}
      {(eventsQ.isError || matricesQ.isError || signalsQ.isError) && (
        <p className="mt-3 text-[11px] text-[#ef4444] tabular-nums">Failed to load convexity radar data.</p>
      )}
    </section>
  );
}
