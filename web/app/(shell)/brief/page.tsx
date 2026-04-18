// Brief page — server-fetches brief_log at request time (edge)
import { BriefRenderer } from '@/components/brief/BriefRenderer';
import { createClient } from '@/lib/supabase/server';
import { getLatestBrief } from '@/lib/supabase/queries';
import type { BriefLogRow } from '@/lib/supabase/queries';

export default async function BriefPage() {
  let initialBrief: BriefLogRow | null = null;
  let initialError: string | null = null;

  try {
    const supabase = await createClient();
    if (!supabase) {
      initialError = 'Supabase not configured';
    } else {
      const { data, error } = await getLatestBrief(supabase);
      if (error) {
        initialError = error.message;
      } else {
        initialBrief = data ?? null;
      }
    }
  } catch (e) {
    initialError = e instanceof Error ? e.message : 'Failed to load brief';
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="font-display text-3xl font-semibold text-neutral-900">Morning brief</h1>
      <BriefRenderer initialBrief={initialBrief} initialError={initialError} />
    </main>
  );
}
