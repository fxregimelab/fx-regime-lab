import { HomeLive } from '@/components/shell/HomeLive';
import { AboutStrip } from '@/components/shell/AboutStrip';
import { SignalArchitectureSection } from '@/components/shell/SignalArchitectureSection';
import { PAIRS, type PairLabel } from '@/lib/constants/pairs';
import {
  getLatestRegimeCalls,
  getSignalsForPair,
  getValidationHomeStrip,
  type ValidationHomeStrip,
} from '@/lib/supabase/queries';
import { createClient } from '@/lib/supabase/server';
import type { RegimeCall } from '@/lib/types/regime';
import type { SignalValue } from '@/lib/types/signal';

export const runtime = 'edge';

function emptyPairRecord<T>(): Record<PairLabel, T | null> {
  return Object.fromEntries(PAIRS.map((p) => [p.label, null])) as Record<PairLabel, T | null>;
}

export default async function HomePage() {
  let initialCalls: Record<PairLabel, RegimeCall | null> = emptyPairRecord<RegimeCall>();
  const initialSignals: Record<PairLabel, SignalValue | null> = emptyPairRecord<SignalValue>();
  let initialStrip: ValidationHomeStrip | null = null;

  try {
    const supabase = await createClient();
    if (supabase) {
      const [regimeRes, stripRes, ...signalRows] = await Promise.all([
        getLatestRegimeCalls(supabase),
        getValidationHomeStrip(supabase),
        ...PAIRS.map((p) => getSignalsForPair(supabase, p.label)),
      ]);

      initialCalls = regimeRes.byPair as Record<PairLabel, RegimeCall | null>;
      initialStrip = stripRes.data;

      PAIRS.forEach((p, i) => {
        const res = signalRows[i];
        if (res && !res.error) {
          initialSignals[p.label] = res.data ?? null;
        }
      });
    }
  } catch {
    /* Upstream error: shell still renders; client may hydrate later. */
  }

  return (
    <main className="min-w-0">
      <HomeLive initialCalls={initialCalls} initialSignals={initialSignals} initialStrip={initialStrip} />
      <SignalArchitectureSection />
      <AboutStrip />
    </main>
  );
}
