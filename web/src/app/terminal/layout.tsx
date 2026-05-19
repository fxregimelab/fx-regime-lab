import { GlobalMacroPulse } from "@/components/layout/global-macro-pulse";
import { TerminalNav } from "@/components/terminal/TerminalNav";
import { TerminalSubNav } from "@/components/terminal/TerminalSubNav";
import { VimNavProvider } from "@/components/terminal/VimNavProvider";
import { AuditTrailBannerServer } from "@/components/ui/audit-trail-banner";
import { CircuitBreaker } from "@/components/ui/circuit-breaker";
import { DensityIndicator } from "@/components/ui/density-indicator";
import {
  getLatestRegimeCalls,
  getLatestSignals,
  getPipelineHealth,
} from "@/lib/supabase/queries";
import type { LatestSignal } from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";
import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Terminal | FX Regime Lab",
  description:
    "Live institutional-grade FX regime terminal. Real-time classifications, cross-asset matrix, and daily briefs for EUR/USD, USD/JPY, and USD/INR.",
};

export default async function TerminalLayout({
  children,
}: {
  children: ReactNode;
}) {
  let lastRunAt: string | null = null;
  let status: "HEALTHY" | "DEGRADED" | "FAILED" | "UNKNOWN" = "UNKNOWN";
  let dqs: number | null = null;
  let errors: string[] = [];
  let signals: Record<string, LatestSignal> = {};

  try {
    const supabase = await createClient();
    const [health, latestSignals, calls] = await Promise.all([
      getPipelineHealth(supabase, 1),
      getLatestSignals(supabase),
      getLatestRegimeCalls(supabase),
    ]);
    if (health.length > 0) {
      const latest = health[0];
      lastRunAt = latest.date;
      status = latest.status;
      dqs = latest.dqs ?? null;
      errors = latest.errors;
    }
    // Fallback: DQS from regime_calls if health_checks doesn't have it
    if (dqs == null) {
      const latestCall = Object.values(calls)[0];
      dqs = latestCall?.data_quality_score ?? null;
    }
    signals = latestSignals;
  } catch {
    // Graceful fallback: banner will show UNKNOWN state
  }

  return (
    <div
      data-surface="terminal"
      className="min-h-screen bg-[var(--color-void)] text-[var(--color-text)] overflow-hidden flex flex-col"
    >
      <VimNavProvider />
      <GlobalMacroPulse />
      <TerminalNav signals={signals} />
      <TerminalSubNav />

      {/* Circuit breaker banner — appears when pipeline is interrupted */}
      <div className="max-w-[1152px] mx-auto px-6 w-full">
        <CircuitBreaker lastRunAt={lastRunAt} status={status} errors={errors} />
      </div>

      <main
        id="main-content"
        className="max-w-[1152px] mx-auto px-6 py-10 pt-4 flex-1 w-full"
      >
        {children}
      </main>

      {/* Footer bar */}
      <div className="max-w-[1152px] mx-auto px-6 w-full flex items-center justify-between">
        <DensityIndicator />
      </div>
      <AuditTrailBannerServer
        variant="terminal"
        lastRunAt={lastRunAt}
        status={status}
        dqs={dqs}
      />
    </div>
  );
}
