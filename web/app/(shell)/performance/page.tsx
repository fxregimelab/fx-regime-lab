// Performance — validation_log metrics + full table
import { PerformanceClient } from '@/components/shell/PerformanceClient';
import { createClient } from '@/lib/supabase/server';
import { getValidationHomeStrip, getValidationLog } from '@/lib/supabase/queries';
import type { ValidationHomeStrip } from '@/lib/supabase/queries';
import type { ValidationRow } from '@/lib/types/validation';

export const runtime = 'edge';

export default async function PerformancePage() {
  let initialStrip: ValidationHomeStrip | null = null;
  let initialRows: ValidationRow[] = [];

  try {
    const supabase = await createClient();
    if (supabase) {
      const [stripRes, logRes] = await Promise.all([
        getValidationHomeStrip(supabase),
        getValidationLog(supabase, { limit: 500 }),
      ]);
      if (!stripRes.error && stripRes.data) {
        initialStrip = stripRes.data;
      }
      if (!logRes.error && logRes.data) {
        initialRows = logRes.data;
      }
    }
  } catch {
    /* client will refetch */
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="font-display text-3xl font-semibold text-neutral-900">Performance</h1>
      <p className="mt-3 max-w-2xl text-neutral-600">
        Public validation trail for G10 FX regime calls. Directional calls only. NEUTRAL predictions are
        excluded from accuracy scoring. Metrics aggregate all pairs in the database (no backdating).
      </p>
      <PerformanceClient initialStrip={initialStrip} initialRows={initialRows} />
    </main>
  );
}
