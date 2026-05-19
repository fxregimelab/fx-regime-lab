export const revalidate = 3600;

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Audit Log | FX Regime Lab",
  description:
    "Immutable audit trail of pipeline health, regime calls, and validation events.",
};

import { PipelineHealthDashboard } from "@/components/audit/PipelineHealthDashboard";
import { AuditTrailBannerServer } from "@/components/ui/audit-trail-banner";
import {
  getLatestAccuracyAlerts,
  getPipelineHealth,
} from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";

export default async function AuditPage() {
  const supabase = await createClient();

  const [health, alerts] = await Promise.all([
    getPipelineHealth(supabase, 14),
    getLatestAccuracyAlerts(supabase),
  ]);

  return (
    <main
      id="main-content"
      className="min-h-screen bg-[var(--color-void)] text-[var(--color-text-secondary)]"
    >
      <header className="border-b border-solid border-[var(--terminal-border)] bg-[var(--terminal-bg)] px-4 py-4">
        <a
          href="/terminal"
          className="font-mono text-[9px] tracking-widest text-[var(--terminal-fg-dim)] no-underline hover:text-[var(--terminal-fg-muted)]"
        >
          ← TERMINAL
        </a>
        <h1 className="mt-3 font-mono text-[11px] font-normal tracking-widest text-[var(--terminal-fg-muted)] tabular-nums">
          [ SYSTEM INTEGRITY LOG ]
        </h1>
        <p className="mt-2 max-w-2xl font-mono text-[10px] leading-relaxed text-[var(--terminal-fg-dim)] tabular-nums">
          Immutable audit trail of all regime calls and validation events.
        </p>
      </header>
      <AuditTrailBannerServer variant="terminal" />
      <div className="mx-auto max-w-3xl space-y-6 px-4 py-6">
        {/* Pipeline Health Dashboard */}
        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-mono text-[10px] tracking-[0.2em] text-[var(--color-text-muted)] uppercase">
              Pipeline Health
            </h2>
            <span className="font-mono text-[9px] text-[var(--color-text-dim)] tabular-nums">
              {new Date().toISOString().slice(0, 10)} UTC
            </span>
          </div>
          <PipelineHealthDashboard health={health} alerts={alerts} />
        </section>

        <article className="border border-solid border-[var(--terminal-border)] bg-[var(--terminal-bg)] p-4 rounded-none">
          <p className="font-mono text-[11px] leading-relaxed text-[var(--terminal-fg-muted)] tabular-nums">
            The full system audit log is maintained in the immutable ledger
            within Supabase. Every regime call, validation outcome, and pipeline
            event is timestamped and append-only.
          </p>
          <p className="mt-4 font-mono text-[10px] leading-relaxed text-[var(--terminal-fg-dim)] tabular-nums">
            For the complete development history, refer to the repository commit
            log on GitHub.
          </p>
          <div className="mt-4 border-t border-[var(--terminal-border)] pt-4">
            <a
              href="/diagnostics"
              className="font-mono text-[10px] tracking-widest text-[var(--terminal-fg-muted)] hover:text-[var(--terminal-fg)] uppercase transition-colors"
            >
              View diagnostic reports →
            </a>
          </div>
        </article>
      </div>
    </main>
  );
}
