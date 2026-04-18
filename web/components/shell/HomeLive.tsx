'use client';

import { type PairLabel } from '@/lib/constants/pairs';
import { useHomeMarketData } from '@/hooks/useHomeMarketData';
import type { ValidationHomeStrip } from '@/lib/supabase/queries';
import type { RegimeCall } from '@/lib/types/regime';
import type { SignalValue } from '@/lib/types/signal';
import { HomeHero } from '@/components/shell/HomeHero';
import { HomePairCards } from '@/components/shell/HomePairCards';
import { TrackRecordStrip } from '@/components/shell/TrackRecordStrip';

type Props = {
  initialCalls: Record<PairLabel, RegimeCall | null>;
  initialSignals: Record<PairLabel, SignalValue | null>;
  initialStrip: ValidationHomeStrip | null;
};

const EUR: PairLabel = 'EURUSD';

export function HomeLive({ initialCalls, initialSignals, initialStrip }: Props) {
  const { calls, signals, pending } = useHomeMarketData({ initialCalls, initialSignals });

  const heroLoading = pending && calls[EUR] == null && signals[EUR] == null;

  return (
    <>
      <HomeHero eurCall={calls[EUR]} eurSignals={signals[EUR]} heroLoading={heroLoading} />
      <div className="pb-20">
        <HomePairCards calls={calls} signals={signals} pending={pending} />
      </div>
      <TrackRecordStrip initialStrip={initialStrip} />
    </>
  );
}
