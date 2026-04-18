'use client';

import { useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { getLatestRegimeCallForPair } from '@/lib/supabase/queries';
import type { RegimeCall } from '@/lib/types/regime';

export function useRegimeCalls(pair: string) {
  const [row, setRow] = useState<RegimeCall | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const supabase = createClient();
        const { data, error: err } = await getLatestRegimeCallForPair(supabase, pair);
        if (cancelled) return;
        if (err) {
          setError(err.message);
          setRow(null);
        } else {
          setError(null);
          setRow(data);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Failed to load regime');
          setRow(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [pair]);

  return { row, loading, error };
}
