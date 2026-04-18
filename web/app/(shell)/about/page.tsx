// About: practitioner-facing background (see docs/DESIGN_SYSTEM.md)
import Image from 'next/image';
import Link from 'next/link';
import { ROUTES } from '@/lib/constants/routes';

export default function AboutPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <div className="grid grid-cols-1 gap-12 md:grid-cols-[minmax(0,1fr)_minmax(0,280px)] md:items-start">
        <div className="order-2 md:order-1">
          <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-neutral-500">
            FX Regime Lab
          </p>
          <h1 className="mt-2 font-display text-3xl font-semibold text-neutral-900">About</h1>

          <section className="mt-10">
            <h2 className="text-lg font-semibold text-neutral-900">What this is</h2>
            <p className="mt-3 text-base leading-relaxed text-neutral-600">
              A live research desk for G10 FX. Every call logged at the moment it is made. Every outcome
              public. The pipeline runs daily; outputs land in Supabase and surface here on the{' '}
              <Link href={ROUTES.home} className="text-accent underline decoration-accent underline-offset-4">
                home
              </Link>{' '}
              desk, in the{' '}
              <Link href={ROUTES.brief} className="text-accent underline decoration-accent underline-offset-4">
                morning brief
              </Link>
              , and in the terminal for pair-level context. Nothing is backdated.
            </p>
          </section>

          <section className="mt-10">
            <h2 className="text-lg font-semibold text-neutral-900">Validation</h2>
            <p className="mt-3 text-base leading-relaxed text-neutral-600">
              Each call is checked against realized next-day direction where the data allows. The full
              trail is in{' '}
              <Link
                href={ROUTES.performance}
                className="text-accent underline decoration-accent underline-offset-4"
              >
                Performance
              </Link>
              , including rolling accuracy and row-level outcomes. If a row does not yet have a scored
              outcome, it stays blank until the window closes.
            </p>
          </section>

          <section className="mt-10">
            <h2 className="text-lg font-semibold text-neutral-900">Who runs it</h2>
            <p className="mt-3 text-base leading-relaxed text-neutral-600">
              <span className="font-semibold text-neutral-800">Shreyash Sakhare</span> builds and operates
              the stack: data pulls, signal merge, regime persistence, and this site. Background: B.Tech
              Electrical Engineering (Pune), working toward discretionary macro with the numbers on the
              record, not slide decks. Target: NTU MFE (Singapore), 2028 intake.
            </p>
            <p className="mt-4 text-base leading-relaxed text-neutral-600">
              Tone and layout follow a simple rule: calm shell for reading, dark terminal for dense
              monitoring. Type is Inter for prose, Fraunces italic for regime labels on cards, JetBrains
              Mono for figures and dates. Accent color is reserved for high-signal links and emphasis, not
              decorative gradients.
            </p>
          </section>

          <section className="mt-10">
            <h2 className="text-lg font-semibold text-neutral-900">Disclaimer</h2>
            <p className="mt-3 text-base leading-relaxed text-neutral-600">
              Research use only. Not investment advice. Markets can gap, regimes flip, and models fail.
              Read the methodology in-repo and draw your own conclusions.
            </p>
          </section>
        </div>

        <aside className="order-1 md:order-2">
          <div className="relative mx-auto w-full max-w-[280px] md:mx-0">
            <Image
              src="/images/shreyash_sakhare.png"
              alt="Shreyash Sakhare"
              width={280}
              height={320}
              className="h-auto w-full rounded-xl object-cover"
            />
          </div>
        </aside>
      </div>
    </main>
  );
}
