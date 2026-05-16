export const revalidate = 3600;

export const metadata = {
  title: "Audit Log | FX Regime Lab",
};

import { PipelineHealthDashboard } from "@/components/audit/PipelineHealthDashboard";
import {
  getPipelineHealth,
  getLatestAccuracyAlerts,
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
      <header className="border-b border-solid border-[#222] bg-[#000000] px-4 py-4">
        <a
          href="/terminal"
          className="font-mono text-[9px] tracking-widest text-[#666] no-underline hover:text-[#aaa]"
        >
          ← TERMINAL
        </a>
        <h1 className="mt-3 font-mono text-[11px] font-normal tracking-widest text-[#888] tabular-nums">
          [ SYSTEM INTEGRITY LOG ]
        </h1>
        <p className="mt-2 max-w-2xl font-mono text-[10px] leading-relaxed text-[#555] tabular-nums">
          Immutable audit trail of all regime calls and validation events.
        </p>
      </header>
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

        <article className="border border-solid border-[#222] bg-[#000000] p-4 rounded-none">
          <p className="font-mono text-[11px] leading-relaxed text-[#9a9a9a] tabular-nums">
            The full system audit log is maintained in the immutable ledger
            within Supabase. Every regime call, validation outcome, and pipeline
            event is timestamped and append-only.
          </p>
          <p className="mt-4 font-mono text-[10px] leading-relaxed text-[#666] tabular-nums">
            For the complete development history, refer to the repository commit
            log on GitHub.
          </p>
        </article>
      </div>
    </main>
  );
}
