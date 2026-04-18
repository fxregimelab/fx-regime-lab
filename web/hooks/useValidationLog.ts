'use client';

import { useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import {
  getValidationHomeStrip,
  getValidationLog,
  getValidationRolling20Display,
} from '@/lib/supabase/queries';
import type { ValidationHomeStrip } from '@/lib/supabase/queries';
import type { AccuracyMetrics, ValidationRow } from '@/lib/types/validation';

function computeAccuracy(rows: ValidationRow[], windowDays: number): AccuracyMetrics {
  const slice = rows.slice(0, windowDays);
  const count1d = slice.filter((r) => r.correct_1d != null).length;
  const correct1d = slice.filter((r) => r.correct_1d === true).length;
  const count5d = slice.filter((r) => r.correct_5d != null).length;
  const correct5d = slice.filter((r) => r.correct_5d === true).length;
  return {
    windowDays,
    count_1d: count1d,
    correct_1d: correct1d,
    rate_1d: count1d ? correct1d / count1d : null,
    count_5d: count5d,
    correct_5d: correct5d,
    rate_5d: count5d ? correct5d / count5d : null,
  };
}

export function useValidationLog(pair?: string, limit = 120, windowDays = 60) {
  const [rows, setRows] = useState<ValidationRow[]>([]);
  const [metrics, setMetrics] = useState<AccuracyMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const supabase = createClient();
        const { data, error: err } = await getValidationLog(supabase, { pair, limit });
        if (cancelled) return;
        if (err) {
          setError(err.message);
          setRows([]);
          setMetrics(null);
        } else {
          setError(null);
          setRows(data);
          setMetrics(computeAccuracy(data, windowDays));
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Failed to load validation');
          setRows([]);
          setMetrics(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [pair, limit, windowDays]);

  return { rows, metrics, loading, error };
}

/** Home track-record strip: mirrors server `getValidationHomeStrip` for client refresh. */
export function useValidationHomeStrip({ initialStrip }: { initialStrip: ValidationHomeStrip | null }) {
  const [strip, setStrip] = useState<ValidationHomeStrip | null>(initialStrip);
  const [loading, setLoading] = useState(() => initialStrip == null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (initialStrip == null) setLoading(true);
      try {
        const supabase = createClient();
        const { data, error: err } = await getValidationHomeStrip(supabase);
        if (cancelled) return;
        if (err) {
          setError(err.message);
        } else {
          setError(null);
          setStrip((prev) => data ?? prev);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Failed to load validation');
        }
      } finally {
        if (!cancelled && initialStrip == null) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [initialStrip]);

  const rolling20Display = strip ? getValidationRolling20Display(strip.recentRows) : '—';

  return { strip, rolling20Display, loading, error };
}
