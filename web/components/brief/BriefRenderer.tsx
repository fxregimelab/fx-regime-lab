// Renders brief text from Supabase brief_log (SSR seed + client refresh)
'use client';

import { useBrief } from '@/hooks/useBrief';
import type { BriefLogRow } from '@/lib/supabase/queries';

type Props = {
  initialBrief: BriefLogRow | null;
  initialError: string | null;
};

export function BriefRenderer({ initialBrief, initialError }: Props) {
  const { brief, loading, error } = useBrief({ initialBrief, initialError });
  const row = brief;
  const err = error;

  if (loading && !row && !err) {
    return <p className="mt-6 text-neutral-600">Loading brief…</p>;
  }
  if (err) {
    return <p className="mt-6 text-red-700">{err}</p>;
  }
  if (!row?.brief_text) {
    return <p className="mt-6 text-neutral-600">No brief text for the latest date.</p>;
  }
  return (
    <article className="mt-6 max-w-none whitespace-pre-wrap text-sm leading-relaxed text-neutral-800">
      {row.brief_text}
    </article>
  );
}
