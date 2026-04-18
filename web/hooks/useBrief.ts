'use client';

import { useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { getLatestBrief, type BriefLogRow } from '@/lib/supabase/queries';

type Options = {
  /** From server `getLatestBrief` (null means no row). */
  initialBrief?: BriefLogRow | null;
  initialError?: string | null;
};

export function useBrief(options?: Options) {
  const { initialBrief, initialError } = options ?? {};
  const serverSeeded =
    options != null && (initialBrief !== undefined || initialError !== undefined);
  const [brief, setBrief] = useState<BriefLogRow | null>(() =>
    serverSeeded ? (initialBrief ?? null) : null,
  );
  const [error, setError] = useState<string | null>(() =>
    serverSeeded ? (initialError ?? null) : null,
  );
  const [loading, setLoading] = useState(() => !serverSeeded);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!serverSeeded) setLoading(true);
      try {
        const supabase = createClient();
        const { data, error: err } = await getLatestBrief(supabase);
        if (cancelled) return;
        if (err) {
          setError(err.message);
          setBrief(null);
        } else {
          setError(null);
          setBrief(data);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Failed to load brief');
          setBrief(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { brief, loading, error };
}
