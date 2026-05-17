import { AlertStrip } from "@/components/dashboard/AlertStrip";
import { CrossAssetMatrix } from "@/components/dashboard/CrossAssetMatrix";
import { DailyBriefPanel } from "@/components/dashboard/DailyBriefPanel";
import { MacroCalendarStrip } from "@/components/dashboard/MacroCalendarStrip";
import { SignalCard } from "@/components/dashboard/SignalCard";
import { SystemStatusBar } from "@/components/dashboard/SystemStatusBar";
import { ResearchDisclaimer } from "@/components/ui/research-disclaimer";
import { PAIRS } from "@/lib/constants";
import {
  getCrossAssetSnapshot,
  getHistoricalRegimeCalls,
  getLatestBrief,
  getLatestRegimeCalls,
  getLatestSignals,
  getMacroEventsToday,
  getValidationLogT5T20,
} from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terminal | FX Regime Lab",
  description:
    "Live institutional-grade FX regime terminal. Real-time signals, cross-asset matrix, and daily briefs for EUR/USD, USD/JPY, and USD/INR.",
};

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
    validationLog,
    ...pairHistories
  ] = await Promise.all([
    getLatestRegimeCalls(supabase),
    getLatestSignals(supabase),
    getCrossAssetSnapshot(supabase),
    getMacroEventsToday(supabase),
    getLatestBrief(supabase),
    getValidationLogT5T20(supabase, 500),
    ...PAIRS.map((p) => getHistoricalRegimeCalls(supabase, p.label, 30)),
  ]);

  // Validated calls count from filtered production log
  const validatedCount = validationLog.filter(
    (r) => r.t5Outcome === "CORRECT" || r.t5Outcome === "WRONG",
  ).length;

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
      {/* Research Disclaimer */}
      <ResearchDisclaimer />

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
        <p className="font-mono text-[9px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-3">
          Systemic Regime Monitor
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

            const pairLog = validationLog.filter((r) => r.pair === p.display);
            const pairValidT5 = pairLog.filter(
              (r) => r.t5Outcome === "CORRECT" || r.t5Outcome === "WRONG",
            );
            const pairValidT20 = pairLog.filter(
              (r) => r.t20Outcome === "CORRECT" || r.t20Outcome === "WRONG",
            );
            const rolling90dAccT5 =
              pairValidT5.length > 0
                ? pairValidT5.filter((r) => r.t5Outcome === "CORRECT").length /
                  pairValidT5.length
                : null;
            const rolling90dAccT20 =
              pairValidT20.length > 0
                ? pairValidT20.filter((r) => r.t20Outcome === "CORRECT")
                    .length / pairValidT20.length
                : null;

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
                rolling90dAccuracyT5={rolling90dAccT5}
                rolling90dAccuracyT20={rolling90dAccT20}
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
