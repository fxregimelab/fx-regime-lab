'use client';

import { useCallback, useEffect, useState } from 'react';
import { PAIRS, type PairLabel } from '@/lib/constants/pairs';
import { createClient } from '@/lib/supabase/client';
import { getLatestRegimeCalls, getSignalsForPair } from '@/lib/supabase/queries';
import type { RegimeCall } from '@/lib/types/regime';
import type { SignalValue } from '@/lib/types/signal';

function emptySignals(): Record<PairLabel, SignalValue | null> {
  return Object.fromEntries(PAIRS.map((p) => [p.label, null])) as Record<PairLabel, SignalValue | null>;
}

function hasAnyMarketData(
  calls: Record<PairLabel, RegimeCall | null>,
  sig: Record<PairLabel, SignalValue | null>,
) {
  return PAIRS.some((p) => calls[p.label] != null || sig[p.label] != null);
}

type Props = {
  initialCalls: Record<PairLabel, RegimeCall | null>;
  initialSignals: Record<PairLabel, SignalValue | null>;
};

export function useHomeMarketData({ initialCalls, initialSignals }: Props) {
  const [calls, setCalls] = useState<Record<PairLabel, RegimeCall | null>>(initialCalls);
  const [signals, setSignals] = useState<Record<PairLabel, SignalValue | null>>(initialSignals);
  /** True until first client fetch finishes when SSR had no rows (drives skeletons). */
  const [pending, setPending] = useState(() => !hasAnyMarketData(initialCalls, initialSignals));

  const refresh = useCallback(async () => {
    try {
      const supabase = createClient();
      const { byPair } = await getLatestRegimeCalls(supabase);
      setCalls(byPair as Record<PairLabel, RegimeCall | null>);

      const nextSignals = emptySignals();
      await Promise.all(
        PAIRS.map(async (p) => {
          const res = await getSignalsForPair(supabase, p.label);
          if (!res.error) {
            nextSignals[p.label] = res.data ?? null;
          }
        }),
      );
      setSignals(nextSignals);
    } catch {
      /* keep previous snapshot */
    } finally {
      setPending(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { calls, signals, pending, refresh };
}
