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
import Link from "next/link";
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
      {/* Navigation header */}
      <header className="max-w-[1152px] mx-auto px-6 py-4 flex items-center justify-between border-b border-[var(--color-border)]">
        <Link
          href="/"
          className="font-serif text-[18px] text-[var(--color-text)] hover:text-[var(--color-brand-amber)] transition-colors"
        >
          ← FX Regime Lab
        </Link>
        <nav className="flex items-center gap-6">
          <Link
            href="/methodology"
            className="text-[12px] text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors"
          >
            Framework
          </Link>
          <Link
            href="/desk"
            className="text-[12px] text-[var(--color-text)] font-medium"
          >
            Terminal
          </Link>
          <Link
            href="/track-record"
            className="text-[12px] text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors"
          >
            Track Record
          </Link>
          <Link
            href="/about"
            className="text-[12px] text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors"
          >
            About
          </Link>
        </nav>
      </header>

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
