'use client';

import Link from 'next/link';
import { PAIRS } from '@/lib/constants/pairs';
import { ROUTES } from '@/lib/constants/routes';
import { RegimeCard } from '@/components/regime/RegimeCard';
import { PipelineStatus } from '@/components/shell/PipelineStatus';
import type { RegimeCall } from '@/lib/types/regime';
import type { SignalValue } from '@/lib/types/signal';

type Props = {
  eurCall: RegimeCall | null;
  eurSignals: SignalValue | null;
  heroLoading: boolean;
};

const eurMeta = PAIRS.find((p) => p.label === 'EURUSD');

export function HomeHero({ eurCall, eurSignals, heroLoading }: Props) {
  const pairDisplay = eurMeta?.display;

  return (
    <section className="mx-auto grid max-w-6xl gap-12 px-4 py-16 lg:grid-cols-2 lg:items-start lg:gap-16">
      <div>
        <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-neutral-500">
          LIVE MACRO STRATEGY · SINCE APRIL 2026
        </p>
        <h1 className="mt-4 font-display text-[38px] font-semibold leading-[1.1] text-neutral-900 md:text-[56px]">
          Building the
          <br />
          track record.
        </h1>
        <p className="mt-6 max-w-[480px] text-[17px] leading-[1.65] text-neutral-600">
          20. EE undergrad. Studying how G10 FX regimes form and break with rate differentials, COT
          positioning, and volatility. Every call logged the moment it is made. Every outcome public.
        </p>
        <div className="mt-8 flex flex-wrap gap-x-8 gap-y-2 text-[15px] font-medium">
          <Link
            href={ROUTES.brief}
            className="text-accent underline decoration-accent underline-offset-4"
          >
            Read today&apos;s brief
          </Link>
          <Link
            href={ROUTES.performance}
            className="text-accent underline decoration-accent underline-offset-4"
          >
            See the validation log
          </Link>
        </div>
        <PipelineStatus />
      </div>
      <div>
        <RegimeCard
          call={eurCall}
          signals={eurSignals}
          loading={heroLoading}
          variant="hero"
          pairDisplay={pairDisplay}
        />
      </div>
    </section>
  );
}
