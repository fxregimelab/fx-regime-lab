import { Nav } from "@/components/shell/Nav";
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

export const revalidate = 3600;

export const metadata: Metadata = {
  title: "Desk | FX Regime Lab",
  description:
    "Live FX regime monitoring desk. Real-time signals, cross-asset matrix, and daily briefs. Experimental research infrastructure — not investment advice.",
};

export default async function DeskLayout({
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
    } else if (calls && Object.values(calls).length > 0) {
      // Fallback: use latest regime call as proxy for pipeline health
      const latestCall = Object.values(calls)[0];
      lastRunAt = latestCall.created_at;
      status = "HEALTHY";
      dqs = latestCall.data_quality_score ?? null;
    }
    if (dqs == null) {
      const latestCall = Object.values(calls)[0];
      dqs = latestCall?.data_quality_score ?? null;
    }
    signals = latestSignals;
  } catch {
    // Graceful fallback
  }

  return (
    <div
      data-surface="terminal"
      className="min-h-screen bg-[var(--color-void)] text-[var(--color-text)] overflow-hidden flex flex-col"
    >
      <Nav />

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
