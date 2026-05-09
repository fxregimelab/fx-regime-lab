import { AlertStrip } from "@/components/dashboard/AlertStrip";
import { CrossAssetMatrix } from "@/components/dashboard/CrossAssetMatrix";
import { DailyBriefPanel } from "@/components/dashboard/DailyBriefPanel";
import { MacroCalendarStrip } from "@/components/dashboard/MacroCalendarStrip";
import { SignalCard } from "@/components/dashboard/SignalCard";
import { SystemStatusBar } from "@/components/dashboard/SystemStatusBar";
import { PAIRS } from "@/lib/constants";
import {
  getCrossAssetSnapshot,
  getHistoricalRegimeCalls,
  getLatestBrief,
  getLatestRegimeCalls,
  getLatestSignals,
  getMacroEventsToday,
  getValidationStats,
} from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export default async function TerminalIndexPage() {
  const supabase = await createClient();

  // Parallel fetch all data
  const [
    calls,
    signals,
    crossAsset,
    macroEvents,
    brief,
    statsT5,
    ...pairHistories
  ] = await Promise.all([
    getLatestRegimeCalls(supabase),
    getLatestSignals(supabase),
    getCrossAssetSnapshot(supabase),
    getMacroEventsToday(supabase),
    getLatestBrief(supabase),
    getValidationStats(supabase, "t5"),
    ...PAIRS.map((p) => getHistoricalRegimeCalls(supabase, p.label, 30)),
  ]);

  // Validated calls count from ALL aggregate
  const allStats = statsT5.find((s) => s.pair === "ALL");
  const validatedCount = allStats?.sampleSize ?? null;

  // DQS and stress from latest regime call (use first available pair's latest)
  const latestCall = Object.values(calls)[0];
  const dqs = latestCall?.data_quality_score ?? null;
  const stressLevel = latestCall?.stress_level ?? null;
  const lastRunAt = latestCall?.created_at ?? null;

  // Empty state: no regime calls available
  const hasCalls = Object.keys(calls).length > 0;
  if (!hasCalls) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="border border-[var(--color-border)] bg-[var(--color-surface)] px-8 py-10 max-w-lg text-center">
          <p className="font-mono text-[12px] tracking-widest text-[var(--color-warn)] mb-3">
            [ NO DATA ]
          </p>
          <p className="font-sans text-[14px] text-[var(--color-text-secondary)] leading-relaxed mb-4">
            No regime calls available. The pipeline may still be processing
            today&apos;s data.
          </p>
          <p className="font-mono text-[9px] text-[var(--color-text-muted)] tracking-wider">
            {new Date().toISOString().slice(0, 10)}{" "}
            {new Date().toISOString().slice(11, 16)} UTC
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* System Status Bar */}
      <SystemStatusBar
        dqs={dqs}
        stressLevel={stressLevel}
        lastRunAt={lastRunAt}
        validatedCount={validatedCount}
      />

      {/* Cross-Asset Matrix */}
      <CrossAssetMatrix data={crossAsset} />

      {/* Alert Strip */}
      <AlertStrip calls={calls} signals={signals} />

      {/* Macro Calendar Strip */}
      <MacroCalendarStrip events={macroEvents} />

      {/* Signal Cards — 3-pair grid */}
      <div className="mb-10">
        <p className="font-mono text-[9px] tracking-[0.2em] text-[var(--color-text-dim)] uppercase mb-3">
          Live Cross-Pair Overview
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-[var(--color-border)]">
          {PAIRS.map((p, i) => {
            const regimeHistory = pairHistories[i];
            const call = calls[p.label];
            const sig = signals[p.label];

            // Extract signal composite history for sparkline from regime_calls
            const signalHistory = regimeHistory
              .map((r) => r.signal_composite)
              .reverse();

            return (
              <SignalCard
                key={p.label}
                pairLabel={p.label}
                call={call ?? null}
                signal={sig ?? null}
                signalHistory={signalHistory}
                regimeHistory={regimeHistory.map((r) => ({
                  date: r.date,
                  regime: r.regime,
                }))}
              />
            );
          })}
        </div>
      </div>

      {/* Daily Brief Panel */}
      <DailyBriefPanel brief={brief} />
    </div>
  );
}
