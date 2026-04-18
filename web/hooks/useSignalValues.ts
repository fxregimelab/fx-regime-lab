'use client';

import { useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { getSignalsForPair } from '@/lib/supabase/queries';
import type { SignalValue } from '@/lib/types/signal';

/** Loads latest `signals` row for a pair (table name unchanged from v1 pipeline). */
export function useSignalValues(pair: string) {
  const [row, setRow] = useState<SignalValue | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const supabase = createClient();
        const { data, error: err } = await getSignalsForPair(supabase, pair);
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
          setError(e instanceof Error ? e.message : 'Failed to load signals');
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
