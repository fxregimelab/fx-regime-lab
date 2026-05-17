import { getPipelineHealth } from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";
import { AuditTrailBanner } from "./audit-trail";

interface AuditTrailBannerServerProps {
  variant: "terminal" | "shell";
}

/**
 * Server component wrapper that fetches pipeline health and renders
 * the audit trail banner. Use this in layouts and pages.
 */
export async function AuditTrailBannerServer({
  variant,
}: AuditTrailBannerServerProps) {
  let lastRunAt: string | null = null;
  let status: "HEALTHY" | "DEGRADED" | "FAILED" | "UNKNOWN" = "UNKNOWN";
  let dqs: number | null = null;

  try {
    const supabase = await createClient();
    const health = await getPipelineHealth(supabase, 1);
    if (health.length > 0) {
      const latest = health[0];
      lastRunAt = latest.date;
      status = latest.status;
      dqs = latest.dqs;
    }
  } catch {
    // Graceful fallback: leave defaults — banner will show UNKNOWN
  }

  return (
    <AuditTrailBanner
      variant={variant}
      lastRunAt={lastRunAt}
      status={status}
      dqs={dqs}
    />
  );
}
