import { getPipelineHealth } from "@/lib/supabase/queries";
import { createClient } from "@/lib/supabase/server";
import { AuditTrailBanner } from "./audit-trail";

interface AuditTrailBannerServerProps {
  variant: "terminal" | "shell";
  /** Optional override props. When provided, skips the redundant DB fetch. */
  lastRunAt?: string | null;
  status?: "HEALTHY" | "DEGRADED" | "FAILED" | "UNKNOWN";
  dqs?: number | null;
}

/**
 * Server component wrapper that renders the audit trail banner.
 * If override props are provided (e.g. from layout), skips the redundant DB fetch.
 */
export async function AuditTrailBannerServer({
  variant,
  lastRunAt: propLastRunAt,
  status: propStatus,
  dqs: propDqs,
}: AuditTrailBannerServerProps) {
  let lastRunAt = propLastRunAt ?? null;
  let status = propStatus ?? "UNKNOWN";
  let dqs = propDqs ?? null;

  // Only fetch if props weren't provided
  const shouldFetch =
    propLastRunAt === undefined &&
    propStatus === undefined &&
    propDqs === undefined;

  if (shouldFetch) {
    try {
      const supabase = await createClient();
      const health = await getPipelineHealth(supabase, 1);
      if (health.length > 0) {
        const latest = health[0];
        lastRunAt = latest.date;
        status = latest.status;
        dqs = latest.dqs ?? null;
      }
    } catch {
      // Graceful fallback: leave defaults — banner will show UNKNOWN
    }
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
